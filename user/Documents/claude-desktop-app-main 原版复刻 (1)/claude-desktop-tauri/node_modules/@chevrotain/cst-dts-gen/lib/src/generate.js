export function genDts(model, options) {
    let contentParts = [];
    contentParts = contentParts.concat(`import type { CstNode, ICstVisitor, IToken } from "chevrotain";`);
    contentParts = contentParts.concat(model.flatMap((node) => genCstNodeTypes(node)));
    if (options.includeVisitorInterface) {
        contentParts = contentParts.concat(genVisitor(options.visitorInterfaceName, model));
    }
    return contentParts.join("\n\n") + "\n";
}
function genCstNodeTypes(node) {
    const nodeCstInterface = genNodeInterface(node);
    const nodeChildrenInterface = genNodeChildrenType(node);
    return [nodeCstInterface, nodeChildrenInterface];
}
function genNodeInterface(node) {
    const nodeInterfaceName = getNodeInterfaceName(node.name);
    const childrenTypeName = getNodeChildrenTypeName(node.name);
    return `export interface ${nodeInterfaceName} extends CstNode {
  name: "${node.name}";
  children: ${childrenTypeName};
}`;
}
function genNodeChildrenType(node) {
    const typeName = getNodeChildrenTypeName(node.name);
    return `export type ${typeName} = {
  ${node.properties.map((property) => genChildProperty(property)).join("\n  ")}
};`;
}
function genChildProperty(prop) {
    const typeName = buildTypeString(prop.type);
    return `${prop.name}${prop.optional ? "?" : ""}: ${typeName}[];`;
}
function genVisitor(name, nodes) {
    return `export interface ${name}<IN, OUT> extends ICstVisitor<IN, OUT> {
  ${nodes.map((node) => genVisitorFunction(node)).join("\n  ")}
}`;
}
function genVisitorFunction(node) {
    const childrenTypeName = getNodeChildrenTypeName(node.name);
    return `${node.name}(children: ${childrenTypeName}, param?: IN): OUT;`;
}
function buildTypeString(type) {
    if (Array.isArray(type)) {
        const typeNames = [...new Set(type.map((t) => getTypeString(t)))];
        const typeString = typeNames.join(" | ");
        return "(" + typeString + ")";
    }
    else {
        return getTypeString(type);
    }
}
function getTypeString(type) {
    if (type.kind === "token") {
        return "IToken";
    }
    return getNodeInterfaceName(type.name);
}
function getNodeInterfaceName(ruleName) {
    return ruleName.charAt(0).toUpperCase() + ruleName.slice(1) + "CstNode";
}
function getNodeChildrenTypeName(ruleName) {
    return ruleName.charAt(0).toUpperCase() + ruleName.slice(1) + "CstChildren";
}
//# sourceMappingURL=generate.js.map