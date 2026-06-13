import { resolveGrammar as orgResolveGrammar } from "../resolver.js";
import { validateGrammar as orgValidateGrammar } from "../checks.js";
import { defaultGrammarResolverErrorProvider, defaultGrammarValidatorErrorProvider, } from "../../errors_public.js";
export function resolveGrammar(options) {
    const actualOptions = Object.assign({ errMsgProvider: defaultGrammarResolverErrorProvider }, options);
    const topRulesTable = {};
    options.rules.forEach((rule) => {
        topRulesTable[rule.name] = rule;
    });
    return orgResolveGrammar(topRulesTable, actualOptions.errMsgProvider);
}
export function validateGrammar(options) {
    var _a;
    const errMsgProvider = (_a = options.errMsgProvider) !== null && _a !== void 0 ? _a : defaultGrammarValidatorErrorProvider;
    return orgValidateGrammar(options.rules, options.tokenTypes, errMsgProvider, options.grammarName);
}
//# sourceMappingURL=gast_resolver_public.js.map