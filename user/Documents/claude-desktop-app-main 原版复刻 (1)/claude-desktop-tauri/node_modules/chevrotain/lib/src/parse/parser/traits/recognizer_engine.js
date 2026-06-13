import { AT_LEAST_ONE_IDX, AT_LEAST_ONE_SEP_IDX, BITS_FOR_METHOD_TYPE, BITS_FOR_OCCURRENCE_IDX, MANY_IDX, MANY_SEP_IDX, OPTION_IDX, OR_IDX, } from "../../grammar/keys.js";
import { isRecognitionException, MismatchedTokenException, NotAllInputParsedException, } from "../../exceptions_public.js";
import { PROD_TYPE } from "../../grammar/lookahead.js";
import { NextTerminalAfterAtLeastOneSepWalker, NextTerminalAfterAtLeastOneWalker, NextTerminalAfterManySepWalker, NextTerminalAfterManyWalker, } from "../../grammar/interpreter.js";
import { DEFAULT_RULE_CONFIG, END_OF_FILE, } from "../parser.js";
import { IN_RULE_RECOVERY_EXCEPTION } from "./recoverable.js";
import { EOF } from "../../../scan/tokens_public.js";
import { augmentTokenTypes, isTokenType, tokenStructuredMatcher, tokenStructuredMatcherNoCategories, } from "../../../scan/tokens.js";
/**
 * This trait is responsible for the runtime parsing engine
 * Used by the official API (recognizer_api.ts)
 */
export class RecognizerEngine {
    initRecognizerEngine(tokenVocabulary, config) {
        this.className = this.constructor.name;
        // TODO: would using an ES6 Map or plain object be faster (CST building scenario)
        this.shortRuleNameToFull = {};
        this.fullRuleNameToShort = {};
        this.ruleShortNameIdx = 256;
        this.tokenMatcher = tokenStructuredMatcherNoCategories;
        this.subruleIdx = 0;
        this.currRuleShortName = 0;
        this.definedRulesNames = [];
        this.tokensMap = {};
        this.isBackTrackingStack = [];
        this.RULE_STACK = [];
        this.RULE_STACK_IDX = -1;
        this.RULE_OCCURRENCE_STACK = [];
        this.RULE_OCCURRENCE_STACK_IDX = -1;
        this.gastProductionsCache = {};
        if (Object.hasOwn(config, "serializedGrammar")) {
            throw Error("The Parser's configuration can no longer contain a <serializedGrammar> property.\n" +
                "\tSee: https://chevrotain.io/docs/changes/BREAKING_CHANGES.html#_6-0-0\n" +
                "\tFor Further details.");
        }
        if (Array.isArray(tokenVocabulary)) {
            // This only checks for Token vocabularies provided as arrays.
            // That is good enough because the main objective is to detect users of pre-V4.0 APIs
            // rather than all edge cases of empty Token vocabularies.
            if (tokenVocabulary.length === 0) {
                throw Error("A Token Vocabulary cannot be empty.\n" +
                    "\tNote that the first argument for the parser constructor\n" +
                    "\tis no longer a Token vector (since v4.0).");
            }
            if (typeof tokenVocabulary[0].startOffset === "number") {
                throw Error("The Parser constructor no longer accepts a token vector as the first argument.\n" +
                    "\tSee: https://chevrotain.io/docs/changes/BREAKING_CHANGES.html#_4-0-0\n" +
                    "\tFor Further details.");
            }
        }
        if (Array.isArray(tokenVocabulary)) {
            this.tokensMap = tokenVocabulary.reduce((acc, tokType) => {
                acc[tokType.name] = tokType;
                return acc;
            }, {});
        }
        else if (Object.hasOwn(tokenVocabulary, "modes") &&
            Object.values(tokenVocabulary.modes)
                .flat()
                .every(isTokenType)) {
            const allTokenTypes = Object.values(tokenVocabulary.modes).flat();
            const uniqueTokens = [...new Set(allTokenTypes)];
            this.tokensMap = uniqueTokens.reduce((acc, tokType) => {
                acc[tokType.name] = tokType;
                return acc;
            }, {});
        }
        else if (typeof tokenVocabulary === "object" &&
            tokenVocabulary !== null) {
            this.tokensMap = Object.assign({}, tokenVocabulary);
        }
        else {
            throw new Error("<tokensDictionary> argument must be An Array of Token constructors," +
                " A dictionary of Token constructors or an IMultiModeLexerDefinition");
        }
        // always add EOF to the tokenNames -> constructors map. it is useful to assure all the input has been
        // parsed with a clear error message ("expecting EOF but found ...")
        this.tokensMap["EOF"] = EOF;
        const allTokenTypes = Object.hasOwn(tokenVocabulary, "modes")
            ? Object.values(tokenVocabulary.modes).flat()
            : Object.values(tokenVocabulary);
        const noTokenCategoriesUsed = allTokenTypes.every(
        // intentional "==" to also cover "undefined"
        (tokenConstructor) => { var _a; return ((_a = tokenConstructor.categoryMatches) === null || _a === void 0 ? void 0 : _a.length) == 0; });
        this.tokenMatcher = noTokenCategoriesUsed
            ? tokenStructuredMatcherNoCategories
            : tokenStructuredMatcher;
        // Because ES2015+ syntax should be supported for creating Token classes
        // We cannot assume that the Token classes were created using the "extendToken" utilities
        // Therefore we must augment the Token classes both on Lexer initialization and on Parser initialization
        augmentTokenTypes(Object.values(this.tokensMap));
    }
    defineRule(ruleName, impl, config) {
        if (this.selfAnalysisDone) {
            throw Error(`Grammar rule <${ruleName}> may not be defined after the 'performSelfAnalysis' method has been called'\n` +
                `Make sure that all grammar rule definitions are done before 'performSelfAnalysis' is called.`);
        }
        const resyncEnabled = Object.hasOwn(config, "resyncEnabled")
            ? config.resyncEnabled // assumes end user provides the correct config value/type
            : DEFAULT_RULE_CONFIG.resyncEnabled;
        const recoveryValueFunc = Object.hasOwn(config, "recoveryValueFunc")
            ? config.recoveryValueFunc // assumes end user provides the correct config value/type
            : DEFAULT_RULE_CONFIG.recoveryValueFunc;
        // performance optimization: Use small integers as keys for the longer human readable "full" rule names.
        // this greatly improves Map access time (as much as 8% for some performance benchmarks).
        const shortName = this.ruleShortNameIdx << (BITS_FOR_METHOD_TYPE + BITS_FOR_OCCURRENCE_IDX);
        this.ruleShortNameIdx++;
        this.shortRuleNameToFull[shortName] = ruleName;
        this.fullRuleNameToShort[ruleName] = shortName;
        let coreRuleFunction;
        // Micro optimization, only check the condition **once** on rule definition
        // instead of **every single** rule invocation.
        if (this.outputCst === true) {
            coreRuleFunction = function invokeRuleWithTry(...args) {
                try {
                    this.ruleInvocationStateUpdate(shortName, ruleName, this.subruleIdx);
                    impl.apply(this, args);
                    const cst = this.CST_STACK[this.CST_STACK.length - 1];
                    this.cstPostRule(cst);
                    return cst;
                }
                catch (e) {
                    return this.invokeRuleCatch(e, resyncEnabled, recoveryValueFunc);
                }
                finally {
                    this.ruleFinallyStateUpdate();
                }
            };
        }
        else {
            coreRuleFunction = function invokeRuleWithTryCst(...args) {
                try {
                    this.ruleInvocationStateUpdate(shortName, ruleName, this.subruleIdx);
                    return impl.apply(this, args);
                }
                catch (e) {
                    return this.invokeRuleCatch(e, resyncEnabled, recoveryValueFunc);
                }
                finally {
                    this.ruleFinallyStateUpdate();
                }
            };
        }
        // wrapper to allow before/after parsing hooks
        const rootRuleFunction = function rootRule(...args) {
            this.onBeforeParse(ruleName);
            try {
                return coreRuleFunction.apply(this, args);
            }
            finally {
                this.onAfterParse(ruleName);
            }
        };
        const wrappedGrammarRule = Object.assign(rootRuleFunction, { ruleName, originalGrammarAction: impl, coreRule: coreRuleFunction });
        return wrappedGrammarRule;
    }
    invokeRuleCatch(e, resyncEnabledConfig, recoveryValueFunc) {
        const isFirstInvokedRule = this.RULE_STACK_IDX === 0;
        // note the reSync is always enabled for the first rule invocation, because we must always be able to
        // reSync with EOF and just output some INVALID ParseTree
        // during backtracking reSync recovery is disabled, otherwise we can't be certain the backtracking
        // path is really the most valid one
        const reSyncEnabled = resyncEnabledConfig && !this.isBackTracking() && this.recoveryEnabled;
        if (isRecognitionException(e)) {
            const recogError = e;
            if (reSyncEnabled) {
                const reSyncTokType = this.findReSyncTokenType();
                if (this.isInCurrentRuleReSyncSet(reSyncTokType)) {
                    recogError.resyncedTokens = this.reSyncTo(reSyncTokType);
                    if (this.outputCst) {
                        const partialCstResult = this.CST_STACK[this.CST_STACK.length - 1];
                        partialCstResult.recoveredNode = true;
                        return partialCstResult;
                    }
                    else {
                        return recoveryValueFunc(e);
                    }
                }
                else {
                    if (this.outputCst) {
                        const partialCstResult = this.CST_STACK[this.CST_STACK.length - 1];
                        partialCstResult.recoveredNode = true;
                        recogError.partialCstResult = partialCstResult;
                    }
                    // to be handled Further up the call stack
                    throw recogError;
                }
            }
            else if (isFirstInvokedRule) {
                // otherwise a Redundant input error will be created as well and we cannot guarantee that this is indeed the case
                this.moveToTerminatedState();
                // the parser should never throw one of its own errors outside its flow.
                // even if error recovery is disabled
                return recoveryValueFunc(e);
            }
            else {
                // to be recovered Further up the call stack
                throw recogError;
            }
        }
        else {
            // some other Error type which we don't know how to handle (for example a built in JavaScript Error)
            throw e;
        }
    }
    // Implementation of parsing DSL
    optionInternal(actionORMethodDef, occurrence) {
        const key = this.getKeyForAutomaticLookahead(OPTION_IDX, occurrence);
        return this.optionInternalLogic(actionORMethodDef, occurrence, key);
    }
    optionInternalLogic(actionORMethodDef, occurrence, key) {
        let lookAheadFunc = this.getLaFuncFromCache(key);
        let action;
        if (typeof actionORMethodDef !== "function") {
            action = actionORMethodDef.DEF;
            const predicate = actionORMethodDef.GATE;
            // predicate present
            if (predicate !== undefined) {
                const orgLookaheadFunction = lookAheadFunc;
                lookAheadFunc = () => {
                    return predicate.call(this) && orgLookaheadFunction.call(this);
                };
            }
        }
        else {
            action = actionORMethodDef;
        }
        if (lookAheadFunc.call(this) === true) {
            return action.call(this);
        }
        return undefined;
    }
    atLeastOneInternal(prodOccurrence, actionORMethodDef) {
        const laKey = this.getKeyForAutomaticLookahead(AT_LEAST_ONE_IDX, prodOccurrence);
        return this.atLeastOneInternalLogic(prodOccurrence, actionORMethodDef, laKey);
    }
    atLeastOneInternalLogic(prodOccurrence, actionORMethodDef, key) {
        let lookAheadFunc = this.getLaFuncFromCache(key);
        let action;
        if (typeof actionORMethodDef !== "function") {
            action = actionORMethodDef.DEF;
            const predicate = actionORMethodDef.GATE;
            // predicate present
            if (predicate !== undefined) {
                const orgLookaheadFunction = lookAheadFunc;
                lookAheadFunc = () => {
                    return predicate.call(this) && orgLookaheadFunction.call(this);
                };
            }
        }
        else {
            action = actionORMethodDef;
        }
        if (lookAheadFunc.call(this) === true) {
            let notStuck = this.doSingleRepetition(action);
            while (lookAheadFunc.call(this) === true &&
                notStuck === true) {
                notStuck = this.doSingleRepetition(action);
            }
        }
        else {
            throw this.raiseEarlyExitException(prodOccurrence, PROD_TYPE.REPETITION_MANDATORY, actionORMethodDef.ERR_MSG);
        }
        // note that while it may seem that this can cause an error because by using a recursive call to
        // AT_LEAST_ONE we change the grammar to AT_LEAST_TWO, AT_LEAST_THREE ... , the possible recursive call
        // from the tryInRepetitionRecovery(...) will only happen IFF there really are TWO/THREE/.... items.
        // Performance optimization: "attemptInRepetitionRecovery" will be defined as NOOP unless recovery is enabled
        this.attemptInRepetitionRecovery(this.atLeastOneInternal, [prodOccurrence, actionORMethodDef], lookAheadFunc, AT_LEAST_ONE_IDX, prodOccurrence, NextTerminalAfterAtLeastOneWalker);
    }
    atLeastOneSepFirstInternal(prodOccurrence, options) {
        const laKey = this.getKeyForAutomaticLookahead(AT_LEAST_ONE_SEP_IDX, prodOccurrence);
        this.atLeastOneSepFirstInternalLogic(prodOccurrence, options, laKey);
    }
    atLeastOneSepFirstInternalLogic(prodOccurrence, options, key) {
        const action = options.DEF;
        const separator = options.SEP;
        const firstIterationLookaheadFunc = this.getLaFuncFromCache(key);
        // 1st iteration
        if (firstIterationLookaheadFunc.call(this) === true) {
            action.call(this);
            //  TODO: Optimization can move this function construction into "attemptInRepetitionRecovery"
            //  because it is only needed in error recovery scenarios.
            const separatorLookAheadFunc = () => {
                return this.tokenMatcher(this.LA_FAST(1), separator);
            };
            // 2nd..nth iterations
            while (this.tokenMatcher(this.LA_FAST(1), separator) === true) {
                // note that this CONSUME will never enter recovery because
                // the separatorLookAheadFunc checks that the separator really does exist.
                this.CONSUME(separator);
                // No need for checking infinite loop here due to consuming the separator.
                action.call(this);
            }
            // Performance optimization: "attemptInRepetitionRecovery" will be defined as NOOP unless recovery is enabled
            this.attemptInRepetitionRecovery(this.repetitionSepSecondInternal, [
                prodOccurrence,
                separator,
                separatorLookAheadFunc,
                action,
                NextTerminalAfterAtLeastOneSepWalker,
            ], separatorLookAheadFunc, AT_LEAST_ONE_SEP_IDX, prodOccurrence, NextTerminalAfterAtLeastOneSepWalker);
        }
        else {
            throw this.raiseEarlyExitException(prodOccurrence, PROD_TYPE.REPETITION_MANDATORY_WITH_SEPARATOR, options.ERR_MSG);
        }
    }
    manyInternal(prodOccurrence, actionORMethodDef) {
        const laKey = this.getKeyForAutomaticLookahead(MANY_IDX, prodOccurrence);
        return this.manyInternalLogic(prodOccurrence, actionORMethodDef, laKey);
    }
    manyInternalLogic(prodOccurrence, actionORMethodDef, key) {
        let lookaheadFunction = this.getLaFuncFromCache(key);
        let action;
        if (typeof actionORMethodDef !== "function") {
            action = actionORMethodDef.DEF;
            const predicate = actionORMethodDef.GATE;
            // predicate present
            if (predicate !== undefined) {
                const orgLookaheadFunction = lookaheadFunction;
                lookaheadFunction = () => {
                    return predicate.call(this) && orgLookaheadFunction.call(this);
                };
            }
        }
        else {
            action = actionORMethodDef;
        }
        let notStuck = true;
        while (lookaheadFunction.call(this) === true && notStuck === true) {
            notStuck = this.doSingleRepetition(action);
        }
        // Performance optimization: "attemptInRepetitionRecovery" will be defined as NOOP unless recovery is enabled
        this.attemptInRepetitionRecovery(this.manyInternal, [prodOccurrence, actionORMethodDef], lookaheadFunction, MANY_IDX, prodOccurrence, NextTerminalAfterManyWalker, 
        // The notStuck parameter is only relevant when "attemptInRepetitionRecovery"
        // is invoked from manyInternal, in the MANY_SEP case and AT_LEAST_ONE[_SEP]
        // An infinite loop cannot occur as:
        // - Either the lookahead is guaranteed to consume something (Single Token Separator)
        // - AT_LEAST_ONE by definition is guaranteed to consume something (or error out).
        notStuck);
    }
    manySepFirstInternal(prodOccurrence, options) {
        const laKey = this.getKeyForAutomaticLookahead(MANY_SEP_IDX, prodOccurrence);
        this.manySepFirstInternalLogic(prodOccurrence, options, laKey);
    }
    manySepFirstInternalLogic(prodOccurrence, options, key) {
        const action = options.DEF;
        const separator = options.SEP;
        const firstIterationLaFunc = this.getLaFuncFromCache(key);
        // 1st iteration
        if (firstIterationLaFunc.call(this) === true) {
            action.call(this);
            const separatorLookAheadFunc = () => {
                return this.tokenMatcher(this.LA_FAST(1), separator);
            };
            // 2nd..nth iterations
            while (this.tokenMatcher(this.LA_FAST(1), separator) === true) {
                // note that this CONSUME will never enter recovery because
                // the separatorLookAheadFunc checks that the separator really does exist.
                this.CONSUME(separator);
                // No need for checking infinite loop here due to consuming the separator.
                action.call(this);
            }
            // Performance optimization: "attemptInRepetitionRecovery" will be defined as NOOP unless recovery is enabled
            this.attemptInRepetitionRecovery(this.repetitionSepSecondInternal, [
                prodOccurrence,
                separator,
                separatorLookAheadFunc,
                action,
                NextTerminalAfterManySepWalker,
            ], separatorLookAheadFunc, MANY_SEP_IDX, prodOccurrence, NextTerminalAfterManySepWalker);
        }
    }
    repetitionSepSecondInternal(prodOccurrence, separator, separatorLookAheadFunc, action, nextTerminalAfterWalker) {
        while (separatorLookAheadFunc()) {
            // note that this CONSUME will never enter recovery because
            // the separatorLookAheadFunc checks that the separator really does exist.
            this.CONSUME(separator);
            action.call(this);
        }
        // we can only arrive to this function after an error
        // has occurred (hence the name 'second') so the following
        // IF will always be entered, its possible to remove it...
        // however it is kept to avoid confusion and be consistent.
        // Performance optimization: "attemptInRepetitionRecovery" will be defined as NOOP unless recovery is enabled
        /* istanbul ignore else */
        this.attemptInRepetitionRecovery(this.repetitionSepSecondInternal, [
            prodOccurrence,
            separator,
            separatorLookAheadFunc,
            action,
            nextTerminalAfterWalker,
        ], separatorLookAheadFunc, AT_LEAST_ONE_SEP_IDX, prodOccurrence, nextTerminalAfterWalker);
    }
    doSingleRepetition(action) {
        const beforeIteration = this.getLexerPosition();
        action.call(this);
        const afterIteration = this.getLexerPosition();
        // This boolean will indicate if this repetition progressed
        // or if we are "stuck" (potential infinite loop in the repetition).
        return afterIteration > beforeIteration;
    }
    orInternal(altsOrOpts, occurrence) {
        const laKey = this.getKeyForAutomaticLookahead(OR_IDX, occurrence);
        const alts = Array.isArray(altsOrOpts) ? altsOrOpts : altsOrOpts.DEF;
        const laFunc = this.getLaFuncFromCache(laKey);
        const altIdxToTake = laFunc.call(this, alts);
        if (altIdxToTake !== undefined) {
            const chosenAlternative = alts[altIdxToTake];
            return chosenAlternative.ALT.call(this);
        }
        this.raiseNoAltException(occurrence, altsOrOpts.ERR_MSG);
    }
    ruleFinallyStateUpdate() {
        this.RULE_STACK_IDX--;
        this.RULE_OCCURRENCE_STACK_IDX--;
        // Restore the cached short name to the parent rule.
        // When the stack is empty (top-level rule exiting), the stale value
        // is harmless — no DSL methods will be called before the next ruleInvocationStateUpdate.
        if (this.RULE_STACK_IDX >= 0) {
            this.currRuleShortName = this.RULE_STACK[this.RULE_STACK_IDX];
        }
        // NOOP when cst is disabled
        this.cstFinallyStateUpdate();
    }
    subruleInternal(ruleToCall, idx, options) {
        let ruleResult;
        try {
            const args = options !== undefined ? options.ARGS : undefined;
            this.subruleIdx = idx;
            // Use coreRule to bypass root-level hooks (onBeforeParse/onAfterParse)
            ruleResult = ruleToCall.coreRule.apply(this, args);
            this.cstPostNonTerminal(ruleResult, options !== undefined && options.LABEL !== undefined
                ? options.LABEL
                : ruleToCall.ruleName);
            return ruleResult;
        }
        catch (e) {
            throw this.subruleInternalError(e, options, ruleToCall.ruleName);
        }
    }
    subruleInternalError(e, options, ruleName) {
        if (isRecognitionException(e) && e.partialCstResult !== undefined) {
            this.cstPostNonTerminal(e.partialCstResult, options !== undefined && options.LABEL !== undefined
                ? options.LABEL
                : ruleName);
            delete e.partialCstResult;
        }
        throw e;
    }
    consumeInternal(tokType, idx, options) {
        let consumedToken;
        try {
            const nextToken = this.LA_FAST(1);
            if (this.tokenMatcher(nextToken, tokType) === true) {
                this.consumeToken();
                consumedToken = nextToken;
            }
            else {
                this.consumeInternalError(tokType, nextToken, options);
            }
        }
        catch (eFromConsumption) {
            consumedToken = this.consumeInternalRecovery(tokType, idx, eFromConsumption);
        }
        this.cstPostTerminal(options !== undefined && options.LABEL !== undefined
            ? options.LABEL
            : tokType.name, consumedToken);
        return consumedToken;
    }
    consumeInternalError(tokType, nextToken, options) {
        let msg;
        const previousToken = this.LA(0);
        if (options !== undefined && options.ERR_MSG) {
            msg = options.ERR_MSG;
        }
        else {
            msg = this.errorMessageProvider.buildMismatchTokenMessage({
                expected: tokType,
                actual: nextToken,
                previous: previousToken,
                ruleName: this.getCurrRuleFullName(),
            });
        }
        throw this.SAVE_ERROR(new MismatchedTokenException(msg, nextToken, previousToken));
    }
    consumeInternalRecovery(tokType, idx, eFromConsumption) {
        // no recovery allowed during backtracking, otherwise backtracking may recover invalid syntax and accept it
        // but the original syntax could have been parsed successfully without any backtracking + recovery
        if (this.recoveryEnabled &&
            // TODO: more robust checking of the exception type. Perhaps Typescript extending expressions?
            eFromConsumption.name === "MismatchedTokenException" &&
            !this.isBackTracking()) {
            const follows = this.getFollowsForInRuleRecovery(tokType, idx);
            try {
                return this.tryInRuleRecovery(tokType, follows);
            }
            catch (eFromInRuleRecovery) {
                if (eFromInRuleRecovery.name === IN_RULE_RECOVERY_EXCEPTION) {
                    // failed in RuleRecovery.
                    // throw the original error in order to trigger reSync error recovery
                    throw eFromConsumption;
                }
                else {
                    throw eFromInRuleRecovery;
                }
            }
        }
        else {
            throw eFromConsumption;
        }
    }
    saveRecogState() {
        // errors is a getter which will clone the errors array
        const savedErrors = this.errors;
        // Slice only the active portion of the pre-allocated stack
        const savedRuleStack = this.RULE_STACK.slice(0, this.RULE_STACK_IDX + 1);
        return {
            errors: savedErrors,
            lexerState: this.exportLexerState(),
            RULE_STACK: savedRuleStack,
            CST_STACK: this.CST_STACK,
        };
    }
    reloadRecogState(newState) {
        this.errors = newState.errors;
        this.importLexerState(newState.lexerState);
        // Copy saved stack back into the pre-allocated array and restore the index
        const saved = newState.RULE_STACK;
        for (let i = 0; i < saved.length; i++) {
            this.RULE_STACK[i] = saved[i];
        }
        this.RULE_STACK_IDX = saved.length - 1;
        // Restore cached short name from the restored stack
        if (this.RULE_STACK_IDX >= 0) {
            this.currRuleShortName = this.RULE_STACK[this.RULE_STACK_IDX];
        }
    }
    ruleInvocationStateUpdate(shortName, fullName, idxInCallingRule) {
        this.RULE_OCCURRENCE_STACK[++this.RULE_OCCURRENCE_STACK_IDX] =
            idxInCallingRule;
        this.RULE_STACK[++this.RULE_STACK_IDX] = shortName;
        this.currRuleShortName = shortName;
        // NOOP when cst is disabled
        this.cstInvocationStateUpdate(fullName);
    }
    isBackTracking() {
        return this.isBackTrackingStack.length !== 0;
    }
    getCurrRuleFullName() {
        const shortName = this.currRuleShortName;
        return this.shortRuleNameToFull[shortName];
    }
    shortRuleNameToFullName(shortName) {
        return this.shortRuleNameToFull[shortName];
    }
    isAtEndOfInput() {
        return this.tokenMatcher(this.LA(1), EOF);
    }
    reset() {
        this.resetLexerState();
        this.subruleIdx = 0;
        this.currRuleShortName = 0;
        this.isBackTrackingStack = [];
        this.errors = [];
        // Reset depth counters but keep arrays allocated to avoid re-allocation.
        // Stale number values in unused slots are harmless.
        this.RULE_STACK_IDX = -1;
        this.RULE_OCCURRENCE_STACK_IDX = -1;
        // TODO: extract a specific reset for TreeBuilder trait
        this.CST_STACK = [];
    }
    /**
     * Hook called before the root-level parsing rule is invoked.
     * This is only called when a rule is invoked directly by the consumer
     * (e.g., `parser.json()`), not when invoked as a sub-rule via SUBRULE.
     *
     * Override this method to perform actions before parsing begins.
     * The default implementation is a no-op.
     *
     * @param ruleName - The name of the root rule being invoked.
     */
    onBeforeParse(ruleName) {
        // Pad with sentinels for bounds-free forward LA()
        for (let i = 0; i < this.maxLookahead + 1; i++) {
            this.tokVector.push(END_OF_FILE);
        }
    }
    /**
     * Hook called after the root-level parsing rule has completed (or thrown).
     * This is only called when a rule is invoked directly by the consumer
     * (e.g., `parser.json()`), not when invoked as a sub-rule via SUBRULE.
     *
     * This hook is called in a `finally` block, so it executes regardless of
     * whether parsing succeeded or threw an error.
     *
     * Override this method to perform actions after parsing completes.
     * The default implementation is a no-op.
     *
     * @param ruleName - The name of the root rule that was invoked.
     */
    onAfterParse(ruleName) {
        if (this.isAtEndOfInput() === false) {
            const firstRedundantTok = this.LA(1);
            const errMsg = this.errorMessageProvider.buildNotAllInputParsedMessage({
                firstRedundant: firstRedundantTok,
                ruleName: this.getCurrRuleFullName(),
            });
            this.SAVE_ERROR(new NotAllInputParsedException(errMsg, firstRedundantTok));
        }
        // undo the padding of sentinels for bounds-free forward LA() in onBeforeParse
        while (this.tokVector.at(-1) === END_OF_FILE) {
            this.tokVector.pop();
        }
    }
}
//# sourceMappingURL=recognizer_engine.js.map