import { DEFAULT_PARSER_CONFIG } from "../parser.js";
import { AT_LEAST_ONE_IDX, AT_LEAST_ONE_SEP_IDX, getKeyForAutomaticLookahead, MANY_IDX, MANY_SEP_IDX, OPTION_IDX, OR_IDX, } from "../../grammar/keys.js";
import { GAstVisitor, getProductionDslName, } from "@chevrotain/gast";
import { LLkLookaheadStrategy } from "../../grammar/llk_lookahead.js";
/**
 * Trait responsible for the lookahead related utilities and optimizations.
 */
export class LooksAhead {
    initLooksAhead(config) {
        this.dynamicTokensEnabled = Object.hasOwn(config, "dynamicTokensEnabled")
            ? config.dynamicTokensEnabled // assumes end user provides the correct config value/type
            : DEFAULT_PARSER_CONFIG.dynamicTokensEnabled;
        this.maxLookahead = Object.hasOwn(config, "maxLookahead")
            ? config.maxLookahead // assumes end user provides the correct config value/type
            : DEFAULT_PARSER_CONFIG.maxLookahead;
        this.lookaheadStrategy = Object.hasOwn(config, "lookaheadStrategy")
            ? config.lookaheadStrategy // assumes end user provides the correct config value/type
            : new LLkLookaheadStrategy({ maxLookahead: this.maxLookahead });
        this.lookAheadFuncsCache = new Map();
    }
    preComputeLookaheadFunctions(rules) {
        rules.forEach((currRule) => {
            this.TRACE_INIT(`${currRule.name} Rule Lookahead`, () => {
                const { alternation, repetition, option, repetitionMandatory, repetitionMandatoryWithSeparator, repetitionWithSeparator, } = collectMethods(currRule);
                alternation.forEach((currProd) => {
                    const prodIdx = currProd.idx === 0 ? "" : currProd.idx;
                    this.TRACE_INIT(`${getProductionDslName(currProd)}${prodIdx}`, () => {
                        const laFunc = this.lookaheadStrategy.buildLookaheadForAlternation({
                            prodOccurrence: currProd.idx,
                            rule: currRule,
                            maxLookahead: currProd.maxLookahead || this.maxLookahead,
                            hasPredicates: currProd.hasPredicates,
                            dynamicTokensEnabled: this.dynamicTokensEnabled,
                        });
                        const key = getKeyForAutomaticLookahead(this.fullRuleNameToShort[currRule.name], OR_IDX, currProd.idx);
                        this.setLaFuncCache(key, laFunc);
                    });
                });
                repetition.forEach((currProd) => {
                    this.computeLookaheadFunc(currRule, currProd.idx, MANY_IDX, "Repetition", currProd.maxLookahead, getProductionDslName(currProd));
                });
                option.forEach((currProd) => {
                    this.computeLookaheadFunc(currRule, currProd.idx, OPTION_IDX, "Option", currProd.maxLookahead, getProductionDslName(currProd));
                });
                repetitionMandatory.forEach((currProd) => {
                    this.computeLookaheadFunc(currRule, currProd.idx, AT_LEAST_ONE_IDX, "RepetitionMandatory", currProd.maxLookahead, getProductionDslName(currProd));
                });
                repetitionMandatoryWithSeparator.forEach((currProd) => {
                    this.computeLookaheadFunc(currRule, currProd.idx, AT_LEAST_ONE_SEP_IDX, "RepetitionMandatoryWithSeparator", currProd.maxLookahead, getProductionDslName(currProd));
                });
                repetitionWithSeparator.forEach((currProd) => {
                    this.computeLookaheadFunc(currRule, currProd.idx, MANY_SEP_IDX, "RepetitionWithSeparator", currProd.maxLookahead, getProductionDslName(currProd));
                });
            });
        });
    }
    computeLookaheadFunc(rule, prodOccurrence, prodKey, prodType, prodMaxLookahead, dslMethodName) {
        this.TRACE_INIT(`${dslMethodName}${prodOccurrence === 0 ? "" : prodOccurrence}`, () => {
            const laFunc = this.lookaheadStrategy.buildLookaheadForOptional({
                prodOccurrence,
                rule,
                maxLookahead: prodMaxLookahead || this.maxLookahead,
                dynamicTokensEnabled: this.dynamicTokensEnabled,
                prodType,
            });
            const key = getKeyForAutomaticLookahead(this.fullRuleNameToShort[rule.name], prodKey, prodOccurrence);
            this.setLaFuncCache(key, laFunc);
        });
    }
    // this actually returns a number, but it is always used as a string (object prop key)
    getKeyForAutomaticLookahead(dslMethodIdx, occurrence) {
        return getKeyForAutomaticLookahead(this.currRuleShortName, dslMethodIdx, occurrence);
    }
    getLaFuncFromCache(key) {
        return this.lookAheadFuncsCache.get(key);
    }
    /* istanbul ignore next */
    setLaFuncCache(key, value) {
        this.lookAheadFuncsCache.set(key, value);
    }
}
class DslMethodsCollectorVisitor extends GAstVisitor {
    constructor() {
        super(...arguments);
        this.dslMethods = {
            option: [],
            alternation: [],
            repetition: [],
            repetitionWithSeparator: [],
            repetitionMandatory: [],
            repetitionMandatoryWithSeparator: [],
        };
    }
    reset() {
        this.dslMethods = {
            option: [],
            alternation: [],
            repetition: [],
            repetitionWithSeparator: [],
            repetitionMandatory: [],
            repetitionMandatoryWithSeparator: [],
        };
    }
    visitOption(option) {
        this.dslMethods.option.push(option);
    }
    visitRepetitionWithSeparator(manySep) {
        this.dslMethods.repetitionWithSeparator.push(manySep);
    }
    visitRepetitionMandatory(atLeastOne) {
        this.dslMethods.repetitionMandatory.push(atLeastOne);
    }
    visitRepetitionMandatoryWithSeparator(atLeastOneSep) {
        this.dslMethods.repetitionMandatoryWithSeparator.push(atLeastOneSep);
    }
    visitRepetition(many) {
        this.dslMethods.repetition.push(many);
    }
    visitAlternation(or) {
        this.dslMethods.alternation.push(or);
    }
}
const collectorVisitor = new DslMethodsCollectorVisitor();
export function collectMethods(rule) {
    collectorVisitor.reset();
    rule.accept(collectorVisitor);
    const dslMethods = collectorVisitor.dslMethods;
    // avoid uncleaned references
    collectorVisitor.reset();
    return dslMethods;
}
//# sourceMappingURL=looksahead.js.map