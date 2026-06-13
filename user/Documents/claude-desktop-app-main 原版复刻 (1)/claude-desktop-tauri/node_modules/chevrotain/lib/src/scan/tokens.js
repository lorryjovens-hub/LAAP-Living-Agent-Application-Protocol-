export function tokenStructuredMatcher(tokInstance, tokConstructor) {
    const instanceType = tokInstance.tokenTypeIdx;
    if (instanceType === tokConstructor.tokenTypeIdx) {
        return true;
    }
    else {
        return (tokConstructor.isParent === true &&
            tokConstructor.categoryMatchesMap[instanceType] === true);
    }
}
// Optimized tokenMatcher in case our grammar does not use token categories
// Being so tiny it is much more likely to be in-lined and this avoid the function call overhead
export function tokenStructuredMatcherNoCategories(token, tokType) {
    return token.tokenTypeIdx === tokType.tokenTypeIdx;
}
export let tokenShortNameIdx = 1;
export const tokenIdxToClass = {};
export function augmentTokenTypes(tokenTypes) {
    // collect the parent Token Types as well.
    const tokenTypesAndParents = expandCategories(tokenTypes);
    // add required tokenType and categoryMatches properties
    assignTokenDefaultProps(tokenTypesAndParents);
    // fill up the categoryMatches
    assignCategoriesMapProp(tokenTypesAndParents);
    assignCategoriesTokensProp(tokenTypesAndParents);
    tokenTypesAndParents.forEach((tokType) => {
        tokType.isParent = tokType.categoryMatches.length > 0;
    });
}
export function expandCategories(tokenTypes) {
    let result = [...tokenTypes];
    let categories = tokenTypes;
    let searching = true;
    while (searching) {
        categories = categories
            .map((currTokType) => currTokType.CATEGORIES)
            .flat()
            .filter(Boolean);
        const newCategories = categories.filter((x) => !result.includes(x));
        result = result.concat(newCategories);
        if (newCategories.length === 0) {
            searching = false;
        }
        else {
            categories = newCategories;
        }
    }
    return result;
}
export function assignTokenDefaultProps(tokenTypes) {
    tokenTypes.forEach((currTokType) => {
        if (!hasShortKeyProperty(currTokType)) {
            tokenIdxToClass[tokenShortNameIdx] = currTokType;
            currTokType.tokenTypeIdx = tokenShortNameIdx++;
        }
        // CATEGORIES? : TokenType | TokenType[]
        if (hasCategoriesProperty(currTokType) &&
            !Array.isArray(currTokType.CATEGORIES)
        // &&
        // !isUndefined(currTokType.CATEGORIES.PATTERN)
        ) {
            currTokType.CATEGORIES = [currTokType.CATEGORIES];
        }
        if (!hasCategoriesProperty(currTokType)) {
            currTokType.CATEGORIES = [];
        }
        if (!hasExtendingTokensTypesProperty(currTokType)) {
            currTokType.categoryMatches = [];
        }
        if (!hasExtendingTokensTypesMapProperty(currTokType)) {
            currTokType.categoryMatchesMap = {};
        }
    });
}
export function assignCategoriesTokensProp(tokenTypes) {
    tokenTypes.forEach((currTokType) => {
        // avoid duplications
        currTokType.categoryMatches = [];
        Object.keys(currTokType.categoryMatchesMap).forEach((key) => {
            currTokType.categoryMatches.push(tokenIdxToClass[key].tokenTypeIdx);
        });
    });
}
export function assignCategoriesMapProp(tokenTypes) {
    tokenTypes.forEach((currTokType) => {
        singleAssignCategoriesToksMap([], currTokType);
    });
}
export function singleAssignCategoriesToksMap(path, nextNode) {
    path.forEach((pathNode) => {
        nextNode.categoryMatchesMap[pathNode.tokenTypeIdx] = true;
    });
    nextNode.CATEGORIES.forEach((nextCategory) => {
        const newPath = path.concat(nextNode);
        // avoids infinite loops due to cyclic categories.
        if (!newPath.includes(nextCategory)) {
            singleAssignCategoriesToksMap(newPath, nextCategory);
        }
    });
}
export function hasShortKeyProperty(tokType) {
    return Object.hasOwn(tokType !== null && tokType !== void 0 ? tokType : {}, "tokenTypeIdx");
}
export function hasCategoriesProperty(tokType) {
    return Object.hasOwn(tokType !== null && tokType !== void 0 ? tokType : {}, "CATEGORIES");
}
export function hasExtendingTokensTypesProperty(tokType) {
    return Object.hasOwn(tokType !== null && tokType !== void 0 ? tokType : {}, "categoryMatches");
}
export function hasExtendingTokensTypesMapProperty(tokType) {
    return Object.hasOwn(tokType !== null && tokType !== void 0 ? tokType : {}, "categoryMatchesMap");
}
export function isTokenType(tokType) {
    return Object.hasOwn(tokType !== null && tokType !== void 0 ? tokType : {}, "tokenTypeIdx");
}
//# sourceMappingURL=tokens.js.map