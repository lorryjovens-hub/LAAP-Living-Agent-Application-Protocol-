#!/usr/bin/env node
const{execSync}=require("child_process");
try{execSync('python3 -c "import laap"',{stdio:"pipe"})}catch{console.log("Installing LAAP...");try{execSync("pip3 install laap",{stdio:"inherit",timeout:120000})}catch{}}