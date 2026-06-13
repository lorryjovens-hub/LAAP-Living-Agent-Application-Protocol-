import { Lexer } from "./lexer_public.js";
import { augmentTokenTypes, tokenStructuredMatcher } from "./tokens.js";
export function tokenLabel(tokType) {
    if (hasTokenLabel(tokType)) {
        return tokType.LABEL;
    }
    else {
        return tokType.name;
    }
}
export function tokenName(tokType) {
    return tokType.name;
}
export function hasTokenLabel(obj) {
    return typeof obj.LABEL === "string" && obj.LABEL !== "";
}
const PARENT = "parent";
const CATEGORIES = "categories";
const LABEL = "label";
const GROUP = "group";
const PUSH_MODE = "push_mode";
const POP_MODE = "pop_mode";
const LONGER_ALT = "longer_alt";
const LINE_BREAKS = "line_breaks";
const START_CHARS_HINT = "start_chars_hint";
export function createToken(config) {
    return createTokenInternal(config);
}
function createTokenInternal(config) {
    const pattern = config.pattern;
    const tokenType = {};
    tokenType.name = config.name;
    if (pattern !== undefined) {
        tokenType.PATTERN = pattern;
    }
    if (Object.hasOwn(config, PARENT)) {
        throw ("The parent property is no longer supported.\n" +
            "See: https://github.com/chevrotain/chevrotain/issues/564#issuecomment-349062346 for details.");
    }
    if (Object.hasOwn(config, CATEGORIES)) {
        // casting to ANY as this will be fixed inside `augmentTokenTypes``
        tokenType.CATEGORIES = config[CATEGORIES];
    }
    augmentTokenTypes([tokenType]);
    if (Object.hasOwn(config, LABEL)) {
        tokenType.LABEL = config[LABEL];
    }
    if (Object.hasOwn(config, GROUP)) {
        tokenType.GROUP = config[GROUP];
    }
    if (Object.hasOwn(config, POP_MODE)) {
        tokenType.POP_MODE = config[POP_MODE];
    }
    if (Object.hasOwn(config, PUSH_MODE)) {
        tokenType.PUSH_MODE = config[PUSH_MODE];
    }
    if (Object.hasOwn(config, LONGER_ALT)) {
        tokenType.LONGER_ALT = config[LONGER_ALT];
    }
    if (Object.hasOwn(config, LINE_BREAKS)) {
        tokenType.LINE_BREAKS = config[LINE_BREAKS];
    }
    if (Object.hasOwn(config, START_CHARS_HINT)) {
        tokenType.START_CHARS_HINT = config[START_CHARS_HINT];
    }
    return tokenType;
}
export const EOF = createToken({ name: "EOF", pattern: Lexer.NA });
augmentTokenTypes([EOF]);
export function createTokenInstance(tokType, image, startOffset, endOffset, startLine, endLine, startColumn, endColumn) {
    return {
        image,
        startOffset,
        endOffset,
        startLine,
        endLine,
        startColumn,
        endColumn,
        tokenTypeIdx: tokType.tokenTypeIdx,
        tokenType: tokType,
    };
}
export function tokenMatcher(token, tokType) {
    return tokenStructuredMatcher(token, tokType);
}
//# sourceMappingURL=tokens_public.js.map