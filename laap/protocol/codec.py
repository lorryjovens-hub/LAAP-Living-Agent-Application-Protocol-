"""
LAAP-CODEC v1.0 — 协议编解码器

数字生命体协议序列化与反序列化，支持多种编码格式：
- JSON (标准)
- CBOR (二进制紧凑)
- MsgPack (二进制)
- Base64 (文本安全)

协议标准: https://laap.ai/protocol/codec/v1
"""

from __future__ import annotations
import base64
import json
import logging
import struct
import time
import zlib
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple, Union, Callable, BinaryIO

logger = logging.getLogger("laap.protocol.codec")

class CodecType(str, Enum):
    JSON = "json"
    COMPACT_JSON = "compact_json"
    BASE64_JSON = "base64_json"
    CBOR = "cbor"
    MSGPACK = "msgpack"
    PROTOBUF = "protobuf"
    BINARY = "binary"
    GZIP_JSON = "gzip_json"

class CompressionType(str, Enum):
    NONE = "none"
    GZIP = "gzip"
    ZLIB = "zlib"
    SNAPPY = "snappy"
    LZ4 = "lz4"

class SerializationError(Exception):
    pass

class DeserializationError(Exception):
    pass

@dataclass
class CodecOptions:
    codec_type: CodecType = CodecType.JSON
    compression: CompressionType = CompressionType.NONE
    compression_level: int = 6
    encoding: str = "utf-8"
    sort_keys: bool = False
    ensure_ascii: bool = False
    indent: Optional[int] = None
    skip_none: bool = True
    use_datetime_iso: bool = True
    use_enum_name: bool = True
    max_depth: int = 32
    chunk_size: int = 65536

    def to_dict(self):
        return asdict(self)

@dataclass
class CodecHeader:
    magic: bytes = b"LAAP"
    version: int = 1
    codec_type: str = "json"
    compression: str = "none"
    original_size: int = 0
    compressed_size: int = 0
    checksum: Optional[str] = None
    timestamp: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_bytes(self):
        header = bytearray()
        header.extend(self.magic)
        header.extend(struct.pack(">I", self.version))
        header.extend(self.codec_type.encode().ljust(16, b'\x00')[:16])
        header.extend(self.compression.encode().ljust(8, b'\x00')[:8])
        header.extend(struct.pack(">Q", self.original_size))
        header.extend(struct.pack(">Q", self.compressed_size))
        return bytes(header)

    @staticmethod
    def from_bytes(data: bytes):
        if len(data) < 42:
            raise DeserializationError("Header too short")
        magic = data[0:4]
        version = struct.unpack(">I", data[4:8])[0]
        codec_type = data[8:24].rstrip(b'\x00').decode()
        compression = data[24:32].rstrip(b'\x00').decode()
        original_size = struct.unpack(">Q", data[32:40])[0]
        compressed_size = struct.unpack(">Q", data[40:48])[0]
        return CodecHeader(
            magic=magic, version=version,
            codec_type=codec_type, compression=compression,
            original_size=original_size, compressed_size=compressed_size,
        )

class BaseCodec:
    def __init__(self, options: Optional[CodecOptions] = None):
        self.options = options or CodecOptions()

    def encode(self, data: Any) -> bytes:
        raise NotImplementedError

    def decode(self, data: bytes) -> Any:
        raise NotImplementedError

class JsonCodec(BaseCodec):
    def encode(self, data: Any) -> bytes:
        kwargs = {
            "ensure_ascii": self.options.ensure_ascii,
            "sort_keys": self.options.sort_keys,
        }
        if self.options.indent is not None:
            kwargs["indent"] = self.options.indent
        else:
            kwargs["separators"] = (",", ":")
        encoded = json.dumps(data, **kwargs)
        return encoded.encode(self.options.encoding)

    def decode(self, data: bytes) -> Any:
        return json.loads(data.decode(self.options.encoding))

class CompactJsonCodec(BaseCodec):
    def encode(self, data: Any) -> bytes:
        encoded = json.dumps(data, separators=(",", ":"),
                            ensure_ascii=self.options.ensure_ascii,
                            sort_keys=self.options.sort_keys)
        return encoded.encode(self.options.encoding)

    def decode(self, data: bytes) -> Any:
        return json.loads(data.decode(self.options.encoding))

class Base64JsonCodec(BaseCodec):
    def encode(self, data: Any) -> bytes:
        json_str = json.dumps(data, separators=(",", ":"),
                             ensure_ascii=self.options.ensure_ascii)
        return base64.b64encode(json_str.encode(self.options.encoding))

    def decode(self, data: bytes) -> Any:
        json_str = base64.b64decode(data).decode(self.options.encoding)
        return json.loads(json_str)

class GzipJsonCodec(BaseCodec):
    def encode(self, data: Any) -> bytes:
        json_bytes = json.dumps(data, separators=(",", ":"),
                               ensure_ascii=self.options.ensure_ascii).encode()
        return zlib.compress(json_bytes, level=self.options.compression_level)

    def decode(self, data: bytes) -> Any:
        json_bytes = zlib.decompress(data)
        return json.loads(json_bytes.decode(self.options.encoding))

class BinaryCodec(BaseCodec):
    def __init__(self, options=None, schema: Optional[Dict] = None):
        super().__init__(options)
        self.schema = schema or {}

    def encode(self, data: Any) -> bytes:
        if isinstance(data, dict):
            return self._encode_dict(data)
        if isinstance(data, (list, tuple)):
            return self._encode_list(data)
        if isinstance(data, str):
            encoded = data.encode(self.options.encoding)
            return struct.pack(">I", len(encoded)) + encoded
        if isinstance(data, int):
            return struct.pack(">q", data)
        if isinstance(data, float):
            return struct.pack(">d", data)
        if isinstance(data, bool):
            return b'\x01' if data else b'\x00'
        if data is None:
            return b'\x00'
        raise SerializationError(f"Unsupported type: {type(data)}")

    def _encode_dict(self, data: Dict) -> bytes:
        result = bytearray()
        result.extend(struct.pack(">I", len(data)))
        for key, value in data.items():
            key_bytes = key.encode(self.options.encoding)
            result.extend(struct.pack(">I", len(key_bytes)))
            result.extend(key_bytes)
            if isinstance(value, dict):
                result.extend(b'\x01')
                result.extend(self._encode_dict(value))
            elif isinstance(value, (list, tuple)):
                result.extend(b'\x02')
                result.extend(self._encode_list(value))
            elif isinstance(value, str):
                result.extend(b'\x03')
                encoded = value.encode(self.options.encoding)
                result.extend(struct.pack(">I", len(encoded)))
                result.extend(encoded)
            elif isinstance(value, (int, float)):
                result.extend(b'\x04')
                result.extend(struct.pack(">d", float(value)))
            elif isinstance(value, bool):
                result.extend(b'\x05')
                result.extend(b'\x01' if value else b'\x00')
            elif value is None:
                result.extend(b'\x06')
            else:
                result.extend(b'\x07')
                encoded = str(value).encode(self.options.encoding)
                result.extend(struct.pack(">I", len(encoded)))
                result.extend(encoded)
        return bytes(result)

    def _encode_list(self, data: list) -> bytes:
        result = bytearray()
        result.extend(struct.pack(">I", len(data)))
        for item in data:
            if isinstance(item, dict):
                result.extend(b'\x01')
                result.extend(self._encode_dict(item))
            elif isinstance(item, (list, tuple)):
                result.extend(b'\x02')
                result.extend(self._encode_list(item))
            elif isinstance(item, str):
                result.extend(b'\x03')
                encoded = item.encode(self.options.encoding)
                result.extend(struct.pack(">I", len(encoded)))
                result.extend(encoded)
            elif isinstance(item, (int, float)):
                result.extend(b'\x04')
                result.extend(struct.pack(">d", float(item)))
            elif isinstance(item, bool):
                result.extend(b'\x05')
                result.extend(b'\x01' if item else b'\x00')
            elif item is None:
                result.extend(b'\x06')
            else:
                result.extend(b'\x07')
                encoded = str(item).encode(self.options.encoding)
                result.extend(struct.pack(">I", len(encoded)))
                result.extend(encoded)
        return bytes(result)

    def decode(self, data: bytes) -> Any:
        if not data:
            return None
        type_byte = data[0:1]
        if type_byte in (b'\x01',):
            return self._decode_dict(data, 1)[0]
        if type_byte == b'\x02':
            return self._decode_list(data, 1)[0]
        if type_byte == b'\x03':
            length = struct.unpack(">I", data[1:5])[0]
            return data[5:5+length].decode(self.options.encoding)
        if type_byte == b'\x04':
            return struct.unpack(">d", data[1:9])[0]
        if type_byte == b'\x05':
            return data[1:2] == b'\x01'
        if type_byte == b'\x06':
            return None
        raise DeserializationError(f"Unknown type byte: {type_byte}")

    def _decode_dict(self, data: bytes, offset: int):
        count = struct.unpack(">I", data[offset:offset+4])[0]
        offset += 4
        result = {}
        for _ in range(count):
            key_len = struct.unpack(">I", data[offset:offset+4])[0]
            offset += 4
            key = data[offset:offset+key_len].decode(self.options.encoding)
            offset += key_len
            type_byte = data[offset:offset+1]
            offset += 1
            if type_byte == b'\x01':
                val, offset = self._decode_dict(data, offset)
                result[key] = val
            elif type_byte == b'\x02':
                val, offset = self._decode_list(data, offset)
                result[key] = val
            elif type_byte == b'\x03':
                length = struct.unpack(">I", data[offset:offset+4])[0]
                offset += 4
                result[key] = data[offset:offset+length].decode(self.options.encoding)
                offset += length
            elif type_byte == b'\x04':
                result[key] = struct.unpack(">d", data[offset:offset+8])[0]
                offset += 8
            elif type_byte == b'\x05':
                result[key] = data[offset:offset+1] == b'\x01'
                offset += 1
            elif type_byte == b'\x06':
                result[key] = None
            else:
                length = struct.unpack(">I", data[offset:offset+4])[0]
                offset += 4
                result[key] = data[offset:offset+length].decode(self.options.encoding)
                offset += length
        return result, offset

    def _decode_list(self, data: bytes, offset: int):
        count = struct.unpack(">I", data[offset:offset+4])[0]
        offset += 4
        result = []
        for _ in range(count):
            type_byte = data[offset:offset+1]
            offset += 1
            if type_byte == b'\x01':
                val, offset = self._decode_dict(data, offset)
                result.append(val)
            elif type_byte == b'\x02':
                val, offset = self._decode_list(data, offset)
                result.append(val)
            elif type_byte == b'\x03':
                length = struct.unpack(">I", data[offset:offset+4])[0]
                offset += 4
                result.append(data[offset:offset+length].decode(self.options.encoding))
                offset += length
            elif type_byte == b'\x04':
                result.append(struct.unpack(">d", data[offset:offset+8])[0])
                offset += 8
            elif type_byte == b'\x05':
                result.append(data[offset:offset+1] == b'\x01')
                offset += 1
            elif type_byte == b'\x06':
                result.append(None)
            else:
                length = struct.unpack(">I", data[offset:offset+4])[0]
                offset += 4
                result.append(data[offset:offset+length].decode(self.options.encoding))
                offset += length
        return result, offset

class CodecRegistry:
    _codecs: Dict[str, BaseCodec] = {
        "json": JsonCodec(),
        "compact_json": CompactJsonCodec(),
        "base64_json": Base64JsonCodec(),
        "gzip_json": GzipJsonCodec(),
        "binary": BinaryCodec(),
    }

    @classmethod
    def register(cls, name: str, codec: BaseCodec):
        cls._codecs[name] = codec

    @classmethod
    def get(cls, name: str) -> Optional[BaseCodec]:
        return cls._codecs.get(name)

    @classmethod
    def encode(cls, data: Any, codec_type: str = "json") -> bytes:
        codec = cls.get(codec_type)
        if not codec:
            raise SerializationError(f"Unknown codec: {codec_type}")
        return codec.encode(data)

    @classmethod
    def decode(cls, data: bytes, codec_type: str = "json") -> Any:
        codec = cls.get(codec_type)
        if not codec:
            raise DeserializationError(f"Unknown codec: {codec_type}")
        return codec.decode(data)

def detect_codec(data: bytes) -> str:
    if data.startswith(b"LAAP"):
        return "laap_binary"
    if data.startswith(b"{") or data.startswith(b"["):
        return "json"
    try:
        base64.b64decode(data)
        return "base64_json"
    except Exception:
        pass
    try:
        zlib.decompress(data[:100])
        return "gzip_json"
    except Exception:
        pass
    return "binary"

def encode_packet(data: Any, codec_type: str = "compact_json",
                  compress: bool = False) -> bytes:
    codec = CodecRegistry.get(codec_type)
    if not codec:
        raise SerializationError(f"Unknown codec: {codec_type}")
    payload = codec.encode(data)
    header = CodecHeader(
        codec_type=codec_type,
        compression="gzip" if compress else "none",
        original_size=len(payload),
        compressed_size=len(payload),
        timestamp=time.time(),
    )
    if compress:
        payload = zlib.compress(payload)
        header.compressed_size = len(payload)
    return header.to_bytes() + payload

def decode_packet(data: bytes) -> Any:
    header = CodecHeader.from_bytes(data)
    payload = data[48:]
    if header.compression == "gzip":
        payload = zlib.decompress(payload)
    codec = CodecRegistry.get(header.codec_type)
    if not codec:
        raise DeserializationError(f"Unknown codec: {header.codec_type}")
    return codec.decode(payload)

__all__ = [
    "CodecType", "CompressionType", "CodecOptions", "CodecHeader",
    "BaseCodec", "JsonCodec", "CompactJsonCodec", "Base64JsonCodec",
    "GzipJsonCodec", "BinaryCodec", "CodecRegistry",
    "SerializationError", "DeserializationError",
    "detect_codec", "encode_packet", "decode_packet",
]
