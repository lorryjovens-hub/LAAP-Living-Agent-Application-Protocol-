import { defineNameProp } from "../../lang/lang_extensions.js";
export function defaultVisit(ctx, param) {
    const childrenNames = Object.keys(ctx);
    const childrenNamesLength = childrenNames.length;
    for (let i = 0; i < childrenNamesLength; i++) {
        const currChildName = childrenNames[i];
        const currChildArray = ctx[currChildName];
        const currChildArrayLength = currChildArray.length;
        for (let j = 0; j < currChildArrayLength; j++) {
            const currChild = currChildArray[j];
            // distinction between Tokens Children and CstNode children
            if (currChild.tokenTypeIdx === undefined) {
                this[currChild.name](currChild.children, param);
            }
        }
    }
    // defaultVisit does not support generic out param
}
export function createBaseSemanticVisitorConstructor(grammarName, ruleNames) {
    const derivedConstructor = function () { };
    // can be overwritten according to:
    // https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Function/
    // name?redirectlocale=en-US&redirectslug=JavaScript%2FReference%2FGlobal_Objects%2FFunction%2Fname
    defineNameProp(derivedConstructor, grammarName + "BaseSemantics");
    const semanticProto = {
        visit: function (cstNode, param) {
            // enables writing more concise visitor methods when CstNode has only a single child
            if (Array.isArray(cstNode)) {
                // A CST Node's children dictionary can never have empty arrays as values
                // If a key is defined there will be at least one element in the corresponding value array.
                cstNode = cstNode[0];
            }
            // enables passing optional CstNodes concisely.
            if (cstNode === undefined) {
                return undefined;
            }
            return this[cstNode.name](cstNode.children, param);
        },
        validateVisitor: function () {
            const semanticDefinitionErrors = validateVisitor(this, ruleNames);
            if (semanticDefinitionErrors.length !== 0) {
                const errorMessages = semanticDefinitionErrors.map((currDefError) => currDefError.msg);
                throw Error(`Errors Detected in CST Visitor <${this.constructor.name}>:\n\t` +
                    `${errorMessages.join("\n\n").replace(/\n/g, "\n\t")}`);
            }
        },
    };
    derivedConstructor.prototype = semanticProto;
    derivedConstructor.prototype.constructor = derivedConstructor;
    derivedConstructor._RULE_NAMES = ruleNames;
    return derivedConstructor;
}
export function createBaseVisitorConstructorWithDefaults(grammarName, ruleNames, baseConstructor) {
    const derivedConstructor = function () { };
    // can be overwritten according to:
    // https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Function/
    // name?redirectlocale=en-US&redirectslug=JavaScript%2FReference%2FGlobal_Objects%2FFunction%2Fname
    defineNameProp(derivedConstructor, grammarName + "BaseSemanticsWithDefaults");
    const withDefaultsProto = Object.create(baseConstructor.prototype);
    ruleNames.forEach((ruleName) => {
        withDefaultsProto[ruleName] = defaultVisit;
    });
    derivedConstructor.prototype = withDefaultsProto;
    derivedConstructor.prototype.constructor = derivedConstructor;
    return derivedConstructor;
}
export var CstVisitorDefinitionError;
(function (CstVisitorDefinitionError) {
    CstVisitorDefinitionError[CstVisitorDefinitionError["REDUNDANT_METHOD"] = 0] = "REDUNDANT_METHOD";
    CstVisitorDefinitionError[CstVisitorDefinitionError["MISSING_METHOD"] = 1] = "MISSING_METHOD";
})(CstVisitorDefinitionError || (CstVisitorDefinitionError = {}));
export function validateVisitor(visitorInstance, ruleNames) {
    const missingErrors = validateMissingCstMethods(visitorInstance, ruleNames);
    return missingErrors;
}
export function validateMissingCstMethods(visitorInstance, ruleNames) {
    const missingRuleNames = ruleNames.filter((currRuleName) => {
        return ((typeof visitorInstance[currRuleName] === "function") === false);
    });
    const errors = missingRuleNames.map((currRuleName) => {
        return {
            msg: `Missing visitor method: <${currRuleName}> on ${(visitorInstance.constructor.name)} CST Visitor.`,
            type: CstVisitorDefinitionError.MISSING_METHOD,
            methodName: currRuleName,
        };
    });
    return errors.filter(Boolean);
}
//# sourceMappingURL=cst_visitor.js.map