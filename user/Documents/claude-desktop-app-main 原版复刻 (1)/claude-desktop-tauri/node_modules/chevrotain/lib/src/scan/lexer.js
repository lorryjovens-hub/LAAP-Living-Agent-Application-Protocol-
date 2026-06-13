import { BaseRegExpVisitor } from "@chevrotain/regexp-to-ast";
import { Lexer, LexerDefinitionErrorType, } from "./lexer_public.js";
import { PRINT_ERROR } from "@chevrotain/utils";
import { canMatchCharCode, failedOptimizationPrefixMsg, getOptimizedStartCodesIndices, } from "./reg_exp.js";
import { getRegExpAst } from "./reg_exp_parser.js";
const PATTERN = "PATTERN";
export const DEFAULT_MODE = "defaultMode";
export const MODES = "modes";
export function analyzeTokenTypes(tokenTypes, options) {
    options = Object.assign({ safeMode: false, positionTracking: "full", lineTerminatorCharacters: ["\r", "\n"], tracer: (msg, action) => action() }, options);
    const tracer = options.tracer;
    tracer("initCharCodeToOptimizedIndexMap", () => {
        initCharCodeToOptimizedIndexMap();
    });
    let onlyRelevantTypes;
    tracer("Reject Lexer.NA", () => {
        onlyRelevantTypes = tokenTypes.filter((currType) => {
            return currType[PATTERN] !== Lexer.NA;
        });
    });
    let hasCustom = false;
    let allTransformedPatterns;
    tracer("Transform Patterns", () => {
        hasCustom = false;
        allTransformedPatterns = onlyRelevantTypes.map((currType) => {
            const currPattern = currType[PATTERN];
            /* istanbul ignore else */
            if (currPattern instanceof RegExp) {
                const regExpSource = currPattern.source;
                if (regExpSource.length === 1 &&
                    // only these regExp meta characters which can appear in a length one regExp
                    regExpSource !== "^" &&
                    regExpSource !== "$" &&
                    regExpSource !== "." &&
                    !currPattern.ignoreCase) {
                    return regExpSource;
                }
                else if (regExpSource.length === 2 &&
                    regExpSource[0] === "\\" &&
                    // not a meta character
                    ![
                        "d",
                        "D",
                        "s",
                        "S",
                        "t",
                        "r",
                        "n",
                        "t",
                        "0",
                        "c",
                        "b",
                        "B",
                        "f",
                        "v",
                        "w",
                        "W",
                    ].includes(regExpSource[1])) {
                    // escaped meta Characters: /\+/ /\[/
                    // or redundant escaping: /\a/
                    // without the escaping "\"
                    return regExpSource[1];
                }
                else {
                    return addStickyFlag(currPattern);
                }
            }
            else if (typeof currPattern === "function") {
                hasCustom = true;
                // CustomPatternMatcherFunc - custom patterns do not require any transformations, only wrapping in a RegExp Like object
                return { exec: currPattern };
            }
            else if (typeof currPattern === "object") {
                hasCustom = true;
                // ICustomPattern
                return currPattern;
            }
            else if (typeof currPattern === "string") {
                if (currPattern.length === 1) {
                    return currPattern;
                }
                else {
                    const escapedRegExpString = currPattern.replace(/[\\^$.*+?()[\]{}|]/g, "\\$&");
                    const wrappedRegExp = new RegExp(escapedRegExpString);
                    return addStickyFlag(wrappedRegExp);
                }
            }
            else {
                throw Error("non exhaustive match");
            }
        });
    });
    let patternIdxToType;
    let patternIdxToGroup;
    let patternIdxToLongerAltIdxArr;
    let patternIdxToPushMode;
    let patternIdxToPopMode;
    tracer("misc mapping", () => {
        patternIdxToType = onlyRelevantTypes.map((currType) => currType.tokenTypeIdx);
        patternIdxToGroup = onlyRelevantTypes.map((clazz) => {
            const groupName = clazz.GROUP;
            /* istanbul ignore next */
            if (groupName === Lexer.SKIPPED) {
                return undefined;
            }
            else if (typeof groupName === "string") {
                return groupName;
            }
            else if (groupName === undefined) {
                return false;
            }
            else {
                throw Error("non exhaustive match");
            }
        });
        patternIdxToLongerAltIdxArr = onlyRelevantTypes.map((clazz) => {
            const longerAltType = clazz.LONGER_ALT;
            if (longerAltType) {
                const longerAltIdxArr = Array.isArray(longerAltType)
                    ? longerAltType.map((type) => onlyRelevantTypes.indexOf(type))
                    : [onlyRelevantTypes.indexOf(longerAltType)];
                return longerAltIdxArr;
            }
        });
        patternIdxToPushMode = onlyRelevantTypes.map((clazz) => clazz.PUSH_MODE);
        patternIdxToPopMode = onlyRelevantTypes.map((clazz) => Object.hasOwn(clazz, "POP_MODE"));
    });
    let patternIdxToCanLineTerminator;
    tracer("Line Terminator Handling", () => {
        const lineTerminatorCharCodes = getCharCodes(options.lineTerminatorCharacters);
        patternIdxToCanLineTerminator = onlyRelevantTypes.map((tokType) => false);
        if (options.positionTracking !== "onlyOffset") {
            patternIdxToCanLineTerminator = onlyRelevantTypes.map((tokType) => {
                if (Object.hasOwn(tokType, "LINE_BREAKS")) {
                    return !!tokType.LINE_BREAKS;
                }
                else {
                    return (checkLineBreaksIssues(tokType, lineTerminatorCharCodes) === false &&
                        canMatchCharCode(lineTerminatorCharCodes, tokType.PATTERN));
                }
            });
        }
    });
    let patternIdxToIsCustom;
    let patternIdxToShort;
    let emptyGroups;
    let patternIdxToConfig;
    tracer("Misc Mapping #2", () => {
        patternIdxToIsCustom = onlyRelevantTypes.map(isCustomPattern);
        patternIdxToShort = allTransformedPatterns.map(isShortPattern);
        emptyGroups = onlyRelevantTypes.reduce((acc, clazz) => {
            const groupName = clazz.GROUP;
            if (typeof groupName === "string" && !(groupName === Lexer.SKIPPED)) {
                acc[groupName] = [];
            }
            return acc;
        }, {});
        patternIdxToConfig = allTransformedPatterns.map((x, idx) => {
            return {
                pattern: allTransformedPatterns[idx],
                longerAlt: patternIdxToLongerAltIdxArr[idx],
                canLineTerminator: patternIdxToCanLineTerminator[idx],
                isCustom: patternIdxToIsCustom[idx],
                short: patternIdxToShort[idx],
                group: patternIdxToGroup[idx],
                push: patternIdxToPushMode[idx],
                pop: patternIdxToPopMode[idx],
                tokenTypeIdx: patternIdxToType[idx],
                tokenType: onlyRelevantTypes[idx],
            };
        });
    });
    let canBeOptimized = true;
    let charCodeToPatternIdxToConfig = [];
    if (!options.safeMode) {
        tracer("First Char Optimization", () => {
            charCodeToPatternIdxToConfig = onlyRelevantTypes.reduce((result, currTokType, idx) => {
                if (typeof currTokType.PATTERN === "string") {
                    const charCode = currTokType.PATTERN.charCodeAt(0);
                    const optimizedIdx = charCodeToOptimizedIndex(charCode);
                    addToMapOfArrays(result, optimizedIdx, patternIdxToConfig[idx]);
                }
                else if (Array.isArray(currTokType.START_CHARS_HINT)) {
                    let lastOptimizedIdx;
                    currTokType.START_CHARS_HINT.forEach((charOrInt) => {
                        const charCode = typeof charOrInt === "string"
                            ? charOrInt.charCodeAt(0)
                            : charOrInt;
                        const currOptimizedIdx = charCodeToOptimizedIndex(charCode);
                        // Avoid adding the config multiple times
                        /* istanbul ignore else */
                        // - Difficult to check this scenario effects as it is only a performance
                        //   optimization that does not change correctness
                        if (lastOptimizedIdx !== currOptimizedIdx) {
                            lastOptimizedIdx = currOptimizedIdx;
                            addToMapOfArrays(result, currOptimizedIdx, patternIdxToConfig[idx]);
                        }
                    });
                }
                else if (currTokType.PATTERN instanceof RegExp) {
                    if (currTokType.PATTERN.unicode) {
                        canBeOptimized = false;
                        if (options.ensureOptimizations) {
                            PRINT_ERROR(`${failedOptimizationPrefixMsg}` +
                                `\tUnable to analyze < ${currTokType.PATTERN.toString()} > pattern.\n` +
                                "\tThe regexp unicode flag is not currently supported by the regexp-to-ast library.\n" +
                                "\tThis will disable the lexer's first char optimizations.\n" +
                                "\tFor details See: https://chevrotain.io/docs/guide/resolving_lexer_errors.html#UNICODE_OPTIMIZE");
                        }
                    }
                    else {
                        const optimizedCodes = getOptimizedStartCodesIndices(currTokType.PATTERN, options.ensureOptimizations);
                        /* istanbul ignore if */
                        // start code will only be empty given an empty regExp or failure of regexp-to-ast library
                        // the first should be a different validation and the second cannot be tested.
                        if (optimizedCodes.length === 0) {
                            // we cannot understand what codes may start possible matches
                            // The optimization correctness requires knowing start codes for ALL patterns.
                            // Not actually sure this is an error, no debug message
                            canBeOptimized = false;
                        }
                        optimizedCodes.forEach((code) => {
                            addToMapOfArrays(result, code, patternIdxToConfig[idx]);
                        });
                    }
                }
                else {
                    if (options.ensureOptimizations) {
                        PRINT_ERROR(`${failedOptimizationPrefixMsg}` +
                            `\tTokenType: <${currTokType.name}> is using a custom token pattern without providing <start_chars_hint> parameter.\n` +
                            "\tThis will disable the lexer's first char optimizations.\n" +
                            "\tFor details See: https://chevrotain.io/docs/guide/resolving_lexer_errors.html#CUSTOM_OPTIMIZE");
                    }
                    canBeOptimized = false;
                }
                return result;
            }, []);
        });
    }
    return {
        emptyGroups: emptyGroups,
        patternIdxToConfig: patternIdxToConfig,
        charCodeToPatternIdxToConfig: charCodeToPatternIdxToConfig,
        hasCustom: hasCustom,
        canBeOptimized: canBeOptimized,
    };
}
export function validatePatterns(tokenTypes, validModesNames) {
    let errors = [];
    const missingResult = findMissingPatterns(tokenTypes);
    errors = errors.concat(missingResult.errors);
    const invalidResult = findInvalidPatterns(missingResult.valid);
    const validTokenTypes = invalidResult.valid;
    errors = errors.concat(invalidResult.errors);
    errors = errors.concat(validateRegExpPattern(validTokenTypes));
    errors = errors.concat(findInvalidGroupType(validTokenTypes));
    errors = errors.concat(findModesThatDoNotExist(validTokenTypes, validModesNames));
    errors = errors.concat(findUnreachablePatterns(validTokenTypes));
    return errors;
}
function validateRegExpPattern(tokenTypes) {
    let errors = [];
    const withRegExpPatterns = tokenTypes.filter((currTokType) => currTokType[PATTERN] instanceof RegExp);
    errors = errors.concat(findEndOfInputAnchor(withRegExpPatterns));
    errors = errors.concat(findStartOfInputAnchor(withRegExpPatterns));
    errors = errors.concat(findUnsupportedFlags(withRegExpPatterns));
    errors = errors.concat(findDuplicatePatterns(withRegExpPatterns));
    errors = errors.concat(findEmptyMatchRegExps(withRegExpPatterns));
    return errors;
}
export function findMissingPatterns(tokenTypes) {
    const tokenTypesWithMissingPattern = tokenTypes.filter((currType) => {
        return !Object.hasOwn(currType, PATTERN);
    });
    const errors = tokenTypesWithMissingPattern.map((currType) => {
        return {
            message: "Token Type: ->" +
                currType.name +
                "<- missing static 'PATTERN' property",
            type: LexerDefinitionErrorType.MISSING_PATTERN,
            tokenTypes: [currType],
        };
    });
    const valid = tokenTypes.filter((x) => !tokenTypesWithMissingPattern.includes(x));
    return { errors, valid };
}
export function findInvalidPatterns(tokenTypes) {
    const tokenTypesWithInvalidPattern = tokenTypes.filter((currType) => {
        const pattern = currType[PATTERN];
        return (!(pattern instanceof RegExp) &&
            !(typeof pattern === "function") &&
            !Object.hasOwn(pattern, "exec") &&
            !(typeof pattern === "string"));
    });
    const errors = tokenTypesWithInvalidPattern.map((currType) => {
        return {
            message: "Token Type: ->" +
                currType.name +
                "<- static 'PATTERN' can only be a RegExp, a" +
                " Function matching the {CustomPatternMatcherFunc} type or an Object matching the {ICustomPattern} interface.",
            type: LexerDefinitionErrorType.INVALID_PATTERN,
            tokenTypes: [currType],
        };
    });
    const valid = tokenTypes.filter((x) => !tokenTypesWithInvalidPattern.includes(x));
    return { errors, valid };
}
const end_of_input = /[^\\][$]/;
export function findEndOfInputAnchor(tokenTypes) {
    class EndAnchorFinder extends BaseRegExpVisitor {
        constructor() {
            super(...arguments);
            this.found = false;
        }
        visitEndAnchor(node) {
            this.found = true;
        }
    }
    const invalidRegex = tokenTypes.filter((currType) => {
        const pattern = currType.PATTERN;
        try {
            const regexpAst = getRegExpAst(pattern);
            const endAnchorVisitor = new EndAnchorFinder();
            endAnchorVisitor.visit(regexpAst);
            return endAnchorVisitor.found;
        }
        catch (e) {
            // old behavior in case of runtime exceptions with regexp-to-ast.
            /* istanbul ignore next - cannot ensure an error in regexp-to-ast*/
            return end_of_input.test(pattern.source);
        }
    });
    const errors = invalidRegex.map((currType) => {
        return {
            message: "Unexpected RegExp Anchor Error:\n" +
                "\tToken Type: ->" +
                currType.name +
                "<- static 'PATTERN' cannot contain end of input anchor '$'\n" +
                "\tSee chevrotain.io/docs/guide/resolving_lexer_errors.html#ANCHORS" +
                "\tfor details.",
            type: LexerDefinitionErrorType.EOI_ANCHOR_FOUND,
            tokenTypes: [currType],
        };
    });
    return errors;
}
export function findEmptyMatchRegExps(tokenTypes) {
    const matchesEmptyString = tokenTypes.filter((currType) => {
        const pattern = currType.PATTERN;
        return pattern.test("");
    });
    const errors = matchesEmptyString.map((currType) => {
        return {
            message: "Token Type: ->" +
                currType.name +
                "<- static 'PATTERN' must not match an empty string",
            type: LexerDefinitionErrorType.EMPTY_MATCH_PATTERN,
            tokenTypes: [currType],
        };
    });
    return errors;
}
const start_of_input = /[^\\[][\^]|^\^/;
export function findStartOfInputAnchor(tokenTypes) {
    class StartAnchorFinder extends BaseRegExpVisitor {
        constructor() {
            super(...arguments);
            this.found = false;
        }
        visitStartAnchor(node) {
            this.found = true;
        }
    }
    const invalidRegex = tokenTypes.filter((currType) => {
        const pattern = currType.PATTERN;
        try {
            const regexpAst = getRegExpAst(pattern);
            const startAnchorVisitor = new StartAnchorFinder();
            startAnchorVisitor.visit(regexpAst);
            return startAnchorVisitor.found;
        }
        catch (e) {
            // old behavior in case of runtime exceptions with regexp-to-ast.
            /* istanbul ignore next - cannot ensure an error in regexp-to-ast*/
            return start_of_input.test(pattern.source);
        }
    });
    const errors = invalidRegex.map((currType) => {
        return {
            message: "Unexpected RegExp Anchor Error:\n" +
                "\tToken Type: ->" +
                currType.name +
                "<- static 'PATTERN' cannot contain start of input anchor '^'\n" +
                "\tSee https://chevrotain.io/docs/guide/resolving_lexer_errors.html#ANCHORS" +
                "\tfor details.",
            type: LexerDefinitionErrorType.SOI_ANCHOR_FOUND,
            tokenTypes: [currType],
        };
    });
    return errors;
}
export function findUnsupportedFlags(tokenTypes) {
    const invalidFlags = tokenTypes.filter((currType) => {
        const pattern = currType[PATTERN];
        return pattern instanceof RegExp && (pattern.multiline || pattern.global);
    });
    const errors = invalidFlags.map((currType) => {
        return {
            message: "Token Type: ->" +
                currType.name +
                "<- static 'PATTERN' may NOT contain global('g') or multiline('m')",
            type: LexerDefinitionErrorType.UNSUPPORTED_FLAGS_FOUND,
            tokenTypes: [currType],
        };
    });
    return errors;
}
// This can only test for identical duplicate RegExps, not semantically equivalent ones.
export function findDuplicatePatterns(tokenTypes) {
    const found = [];
    let identicalPatterns = tokenTypes.map((outerType) => {
        return tokenTypes.reduce((result, innerType) => {
            if (outerType.PATTERN.source === innerType.PATTERN.source &&
                !found.includes(innerType) &&
                innerType.PATTERN !== Lexer.NA) {
                // this avoids duplicates in the result, each Token Type may only appear in one "set"
                // in essence we are creating Equivalence classes on equality relation.
                found.push(innerType);
                result.push(innerType);
                return result;
            }
            return result;
        }, []);
    });
    identicalPatterns = identicalPatterns.filter(Boolean);
    const duplicatePatterns = identicalPatterns.filter((currIdenticalSet) => {
        return currIdenticalSet.length > 1;
    });
    const errors = duplicatePatterns.map((setOfIdentical) => {
        const tokenTypeNames = setOfIdentical.map((currType) => {
            return currType.name;
        });
        const dupPatternSrc = setOfIdentical[0].PATTERN;
        return {
            message: `The same RegExp pattern ->${dupPatternSrc}<-` +
                `has been used in all of the following Token Types: ${tokenTypeNames.join(", ")} <-`,
            type: LexerDefinitionErrorType.DUPLICATE_PATTERNS_FOUND,
            tokenTypes: setOfIdentical,
        };
    });
    return errors;
}
export function findInvalidGroupType(tokenTypes) {
    const invalidTypes = tokenTypes.filter((clazz) => {
        if (!Object.hasOwn(clazz, "GROUP")) {
            return false;
        }
        const group = clazz.GROUP;
        return (group !== Lexer.SKIPPED &&
            group !== Lexer.NA &&
            !(typeof group === "string"));
    });
    const errors = invalidTypes.map((currType) => {
        return {
            message: "Token Type: ->" +
                currType.name +
                "<- static 'GROUP' can only be Lexer.SKIPPED/Lexer.NA/A String",
            type: LexerDefinitionErrorType.INVALID_GROUP_TYPE_FOUND,
            tokenTypes: [currType],
        };
    });
    return errors;
}
export function findModesThatDoNotExist(tokenTypes, validModes) {
    const invalidModes = tokenTypes.filter((clazz) => {
        return (clazz.PUSH_MODE !== undefined && !validModes.includes(clazz.PUSH_MODE));
    });
    const errors = invalidModes.map((tokType) => {
        const msg = `Token Type: ->${tokType.name}<- static 'PUSH_MODE' value cannot refer to a Lexer Mode ->${tokType.PUSH_MODE}<-` +
            `which does not exist`;
        return {
            message: msg,
            type: LexerDefinitionErrorType.PUSH_MODE_DOES_NOT_EXIST,
            tokenTypes: [tokType],
        };
    });
    return errors;
}
export function findUnreachablePatterns(tokenTypes) {
    const errors = [];
    const canBeTested = tokenTypes.reduce((result, tokType, idx) => {
        const pattern = tokType.PATTERN;
        if (pattern === Lexer.NA) {
            return result;
        }
        // a more comprehensive validation for all forms of regExps would require
        // deeper regExp analysis capabilities
        if (typeof pattern === "string") {
            result.push({ str: pattern, idx, tokenType: tokType });
        }
        else if (pattern instanceof RegExp && noMetaChar(pattern)) {
            result.push({ str: pattern.source, idx, tokenType: tokType });
        }
        return result;
    }, []);
    tokenTypes.forEach((aTokType, aIdx) => {
        canBeTested.forEach(({ str: bStr, idx: bIdx, tokenType: bTokType }) => {
            if (aIdx < bIdx && tryToMatchStrToPattern(bStr, aTokType.PATTERN)) {
                const msg = `Token: ->${bTokType.name}<- can never be matched.\n` +
                    `Because it appears AFTER the Token Type ->${aTokType.name}<-` +
                    `in the lexer's definition.\n` +
                    `See https://chevrotain.io/docs/guide/resolving_lexer_errors.html#UNREACHABLE`;
                errors.push({
                    message: msg,
                    type: LexerDefinitionErrorType.UNREACHABLE_PATTERN,
                    tokenTypes: [aTokType, bTokType],
                });
            }
        });
    });
    return errors;
}
function tryToMatchStrToPattern(str, pattern) {
    if (pattern instanceof RegExp) {
        if (usesLookAheadOrBehind(pattern)) {
            // if lookahead or lookbehind assertions are used
            // we assume they would be responsible for disambiguating the match
            // The alternative is to risk false positive unreachable pattern errors.
            // e.g.: /(?<!a)b/ and /b/ tokens would cause such false positives.
            return false;
        }
        const regExpArray = pattern.exec(str);
        return regExpArray !== null && regExpArray.index === 0;
    }
    else if (typeof pattern === "function") {
        // maintain the API of custom patterns
        return pattern(str, 0, [], {});
    }
    else if (Object.hasOwn(pattern, "exec")) {
        // maintain the API of custom patterns
        return pattern.exec(str, 0, [], {});
    }
    else if (typeof pattern === "string") {
        return pattern === str;
    }
    else {
        throw Error("non exhaustive match");
    }
}
function noMetaChar(regExp) {
    //https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/RegExp
    const metaChars = [
        ".",
        "\\",
        "[",
        "]",
        "|",
        "^",
        "$",
        "(",
        ")",
        "?",
        "*",
        "+",
        "{",
    ];
    return (metaChars.find((char) => regExp.source.indexOf(char) !== -1) === undefined);
}
function usesLookAheadOrBehind(regExp) {
    return /(\(\?=)|(\(\?!)|(\(\?<=)|(\(\?<!)/.test(regExp.source);
}
export function addStartOfInput(pattern) {
    const flags = pattern.ignoreCase ? "i" : "";
    // always wrapping in a none capturing group preceded by '^' to make sure matching can only work on start of input.
    // duplicate/redundant start of input markers have no meaning (/^^^^A/ === /^A/)
    return new RegExp(`^(?:${pattern.source})`, flags);
}
export function addStickyFlag(pattern) {
    const flags = pattern.ignoreCase ? "iy" : "y";
    return new RegExp(`${pattern.source}`, flags);
}
export function performRuntimeChecks(lexerDefinition, trackLines, lineTerminatorCharacters) {
    const errors = [];
    // some run time checks to help the end users.
    if (!Object.hasOwn(lexerDefinition, DEFAULT_MODE)) {
        errors.push({
            message: "A MultiMode Lexer cannot be initialized without a <" +
                DEFAULT_MODE +
                "> property in its definition\n",
            type: LexerDefinitionErrorType.MULTI_MODE_LEXER_WITHOUT_DEFAULT_MODE,
        });
    }
    if (!Object.hasOwn(lexerDefinition, MODES)) {
        errors.push({
            message: "A MultiMode Lexer cannot be initialized without a <" +
                MODES +
                "> property in its definition\n",
            type: LexerDefinitionErrorType.MULTI_MODE_LEXER_WITHOUT_MODES_PROPERTY,
        });
    }
    if (Object.hasOwn(lexerDefinition, MODES) &&
        Object.hasOwn(lexerDefinition, DEFAULT_MODE) &&
        !Object.hasOwn(lexerDefinition.modes, lexerDefinition.defaultMode)) {
        errors.push({
            message: `A MultiMode Lexer cannot be initialized with a ${DEFAULT_MODE}: <${lexerDefinition.defaultMode}>` +
                `which does not exist\n`,
            type: LexerDefinitionErrorType.MULTI_MODE_LEXER_DEFAULT_MODE_VALUE_DOES_NOT_EXIST,
        });
    }
    if (Object.hasOwn(lexerDefinition, MODES)) {
        Object.keys(lexerDefinition.modes).forEach((currModeName) => {
            const currModeValue = lexerDefinition.modes[currModeName];
            currModeValue.forEach((currTokType, currIdx) => {
                if (currTokType === undefined) {
                    errors.push({
                        message: `A Lexer cannot be initialized using an undefined Token Type. Mode:` +
                            `<${currModeName}> at index: <${currIdx}>\n`,
                        type: LexerDefinitionErrorType.LEXER_DEFINITION_CANNOT_CONTAIN_UNDEFINED,
                    });
                }
                else if (Object.hasOwn(currTokType, "LONGER_ALT")) {
                    const longerAlt = Array.isArray(currTokType.LONGER_ALT)
                        ? currTokType.LONGER_ALT
                        : [currTokType.LONGER_ALT];
                    longerAlt.forEach((currLongerAlt) => {
                        if (currLongerAlt !== undefined &&
                            !currModeValue.includes(currLongerAlt)) {
                            errors.push({
                                message: `A MultiMode Lexer cannot be initialized with a longer_alt <${currLongerAlt.name}> on token <${currTokType.name}> outside of mode <${currModeName}>\n`,
                                type: LexerDefinitionErrorType.MULTI_MODE_LEXER_LONGER_ALT_NOT_IN_CURRENT_MODE,
                            });
                        }
                    });
                }
            });
        });
    }
    return errors;
}
export function performWarningRuntimeChecks(lexerDefinition, trackLines, lineTerminatorCharacters) {
    const warnings = [];
    let hasAnyLineBreak = false;
    const allTokenTypes = Object.values(lexerDefinition.modes || {})
        .flat()
        .filter(Boolean);
    const concreteTokenTypes = allTokenTypes.filter((currType) => currType[PATTERN] !== Lexer.NA);
    const terminatorCharCodes = getCharCodes(lineTerminatorCharacters);
    if (trackLines) {
        concreteTokenTypes.forEach((tokType) => {
            const currIssue = checkLineBreaksIssues(tokType, terminatorCharCodes);
            if (currIssue !== false) {
                const message = buildLineBreakIssueMessage(tokType, currIssue);
                const warningDescriptor = {
                    message,
                    type: currIssue.issue,
                    tokenType: tokType,
                };
                warnings.push(warningDescriptor);
            }
            else {
                // we don't want to attempt to scan if the user explicitly specified the line_breaks option.
                if (Object.hasOwn(tokType, "LINE_BREAKS")) {
                    if (tokType.LINE_BREAKS === true) {
                        hasAnyLineBreak = true;
                    }
                }
                else {
                    if (canMatchCharCode(terminatorCharCodes, tokType.PATTERN)) {
                        hasAnyLineBreak = true;
                    }
                }
            }
        });
    }
    if (trackLines && !hasAnyLineBreak) {
        warnings.push({
            message: "Warning: No LINE_BREAKS Found.\n" +
                "\tThis Lexer has been defined to track line and column information,\n" +
                "\tBut none of the Token Types can be identified as matching a line terminator.\n" +
                "\tSee https://chevrotain.io/docs/guide/resolving_lexer_errors.html#LINE_BREAKS \n" +
                "\tfor details.",
            type: LexerDefinitionErrorType.NO_LINE_BREAKS_FLAGS,
        });
    }
    return warnings;
}
export function cloneEmptyGroups(emptyGroups) {
    const clonedResult = {};
    const groupKeys = Object.keys(emptyGroups);
    groupKeys.forEach((currKey) => {
        const currGroupValue = emptyGroups[currKey];
        /* istanbul ignore else */
        if (Array.isArray(currGroupValue)) {
            clonedResult[currKey] = [];
        }
        else {
            throw Error("non exhaustive match");
        }
    });
    return clonedResult;
}
// TODO: refactor to avoid duplication
export function isCustomPattern(tokenType) {
    const pattern = tokenType.PATTERN;
    /* istanbul ignore else */
    if (pattern instanceof RegExp) {
        return false;
    }
    else if (typeof pattern === "function") {
        // CustomPatternMatcherFunc - custom patterns do not require any transformations, only wrapping in a RegExp Like object
        return true;
    }
    else if (Object.hasOwn(pattern, "exec")) {
        // ICustomPattern
        return true;
    }
    else if (typeof pattern === "string") {
        return false;
    }
    else {
        throw Error("non exhaustive match");
    }
}
export function isShortPattern(pattern) {
    if (typeof pattern === "string" && pattern.length === 1) {
        return pattern.charCodeAt(0);
    }
    else {
        return false;
    }
}
/**
 * Faster than using a RegExp for default newline detection during lexing.
 */
export const LineTerminatorOptimizedTester = {
    // implements /\n|\r\n?/g.test
    test: function (text) {
        const len = text.length;
        for (let i = this.lastIndex; i < len; i++) {
            const c = text.charCodeAt(i);
            if (c === 10) {
                this.lastIndex = i + 1;
                return true;
            }
            else if (c === 13) {
                if (text.charCodeAt(i + 1) === 10) {
                    this.lastIndex = i + 2;
                }
                else {
                    this.lastIndex = i + 1;
                }
                return true;
            }
        }
        return false;
    },
    lastIndex: 0,
};
function checkLineBreaksIssues(tokType, lineTerminatorCharCodes) {
    if (Object.hasOwn(tokType, "LINE_BREAKS")) {
        // if the user explicitly declared the line_breaks option we will respect their choice
        // and assume it is correct.
        return false;
    }
    else {
        /* istanbul ignore else */
        if (tokType.PATTERN instanceof RegExp) {
            try {
                // TODO: why is the casting suddenly needed?
                canMatchCharCode(lineTerminatorCharCodes, tokType.PATTERN);
            }
            catch (e) {
                /* istanbul ignore next - to test this we would have to mock <canMatchCharCode> to throw an error */
                return {
                    issue: LexerDefinitionErrorType.IDENTIFY_TERMINATOR,
                    errMsg: e.message,
                };
            }
            return false;
        }
        else if (typeof tokType.PATTERN === "string") {
            // string literal patterns can always be analyzed to detect line terminator usage
            return false;
        }
        else if (isCustomPattern(tokType)) {
            // custom token types
            return { issue: LexerDefinitionErrorType.CUSTOM_LINE_BREAK };
        }
        else {
            throw Error("non exhaustive match");
        }
    }
}
export function buildLineBreakIssueMessage(tokType, details) {
    /* istanbul ignore else */
    if (details.issue === LexerDefinitionErrorType.IDENTIFY_TERMINATOR) {
        return ("Warning: unable to identify line terminator usage in pattern.\n" +
            `\tThe problem is in the <${tokType.name}> Token Type\n` +
            `\t Root cause: ${details.errMsg}.\n` +
            "\tFor details See: https://chevrotain.io/docs/guide/resolving_lexer_errors.html#IDENTIFY_TERMINATOR");
    }
    else if (details.issue === LexerDefinitionErrorType.CUSTOM_LINE_BREAK) {
        return ("Warning: A Custom Token Pattern should specify the <line_breaks> option.\n" +
            `\tThe problem is in the <${tokType.name}> Token Type\n` +
            "\tFor details See: https://chevrotain.io/docs/guide/resolving_lexer_errors.html#CUSTOM_LINE_BREAK");
    }
    else {
        throw Error("non exhaustive match");
    }
}
function getCharCodes(charsOrCodes) {
    const charCodes = charsOrCodes.map((numOrString) => {
        if (typeof numOrString === "string") {
            return numOrString.charCodeAt(0);
        }
        else {
            return numOrString;
        }
    });
    return charCodes;
}
function addToMapOfArrays(map, key, value) {
    if (map[key] === undefined) {
        map[key] = [value];
    }
    else {
        map[key].push(value);
    }
}
export const minOptimizationVal = 256;
/**
 * We are mapping charCode above ASCI (256) into buckets each in the size of 256.
 * This is because ASCI are the most common start chars so each one of those will get its own
 * possible token configs vector.
 *
 * Tokens starting with charCodes "above" ASCI are uncommon, so we can "afford"
 * to place these into buckets of possible token configs, What we gain from
 * this is avoiding the case of creating an optimization 'charCodeToPatternIdxToConfig'
 * which would contain 10,000+ arrays of small size (e.g unicode Identifiers scenario).
 * Our 'charCodeToPatternIdxToConfig' max size will now be:
 * 256 + (2^16 / 2^8) - 1 === 511
 *
 * note the hack for fast division integer part extraction
 * See: https://stackoverflow.com/a/4228528
 */
let charCodeToOptimizedIdxMap = [];
export function charCodeToOptimizedIndex(charCode) {
    return charCode < minOptimizationVal
        ? charCode
        : charCodeToOptimizedIdxMap[charCode];
}
/**
 * This is a compromise between cold start / hot running performance
 * Creating this array takes ~3ms on a modern machine,
 * But if we perform the computation at runtime as needed the CSS Lexer benchmark
 * performance degrades by ~10%
 *
 * TODO: Perhaps it should be lazy initialized only if a charCode > 255 is used.
 */
function initCharCodeToOptimizedIndexMap() {
    if (charCodeToOptimizedIdxMap.length === 0) {
        charCodeToOptimizedIdxMap = new Array(65536);
        for (let i = 0; i < 65536; i++) {
            charCodeToOptimizedIdxMap[i] = i > 255 ? 255 + ~~(i / 255) : i;
        }
    }
}
//# sourceMappingURL=lexer.js.map