#!/usr/bin/env node
const{execSync,spawn}=require("child_process");
function findPython(){for(const c of["python3","python"]){try{execSync(c+' -c "import laap;print()"',{encoding:"utf8",stdio:["pipe","pipe","ignore"]});return c}catch{}}console.error("pip install laap");process.exit(1)}
const p=findPython();const pr=spawn(p,["-m","laap.api.cli",...process.argv.slice(2)],{stdio:"inherit",env:{...process.env}});pr.on("exit",c=>process.exit(c));pr.on("error",e=>{console.error(e.message);process.exit(1)});
