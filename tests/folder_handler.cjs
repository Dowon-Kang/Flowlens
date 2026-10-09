// Node unit harness for the actual folder change handler. Not a browser or bridge.
const fs = require('node:fs');
const vm = require('node:vm');
(async () => {
  const input=JSON.parse(fs.readFileSync(0,'utf8'));
  const app=fs.readFileSync('static/app.js','utf8');
  const start=app.indexOf('async function prepareFolderSelection(');
  const handlerStart=app.indexOf("$('folderInput').addEventListener('change',");
  const end=app.indexOf("\ndocument.addEventListener('click',",handlerStart);
  if(handlerStart<0||end<0)throw Error('Folder handler boundary not found');
  const output={read:[],notices:[],requests:[],payload:null};let handler;
  const sandbox={console,TextDecoder,Uint8Array,AbortSignal,
    state:{busy:false},setBusy:v=>sandbox.state.busy=v,
    $:()=>({addEventListener:(name,fn)=>handler=fn}),
    notice:(message,error=false)=>output.notices.push({message,error}),
    analyze:async payload=>{output.payload=payload;},
    fetch:async (url,options)=>{output.requests.push({url,body:JSON.parse(options.body)});return {ok:true,json:async()=>input.plan};}
  };
  vm.runInNewContext(app.slice(start>=0?start:handlerStart,end),sandbox);
  const raw=input.files.map(f=>({
    name:f.path.split('/').at(-1),webkitRelativePath:f.path,
    size:Buffer.byteLength(f.content,'utf8'),
    text:async()=>{output.read.push(f.path);return f.content;},
    arrayBuffer:async()=>{output.read.push(f.path);const b=Buffer.from(f.content,'utf8');return b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength);}
  }));
  await handler({target:{files:raw,value:'selected'}});
  process.stdout.write(JSON.stringify(output));
})().catch(e=>{console.error(e);process.exit(1);});
