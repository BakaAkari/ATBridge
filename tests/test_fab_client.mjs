import assert from 'node:assert/strict';
import {fabRequest} from '../companion/extension/fab-client.mjs';
const listing='f186c225-178a-482b-a122-5508a318a4f0', file='f0828f52-7f32-4f37-b066-c233568e7659';
const params={listing,file,name:'asset_low.zip',size:100};
function response(data,status=200,type='application/json') {
  return {ok:status===200,status,url:'https://www.fab.com/i/example',headers:{get:()=>type},json:async()=>data};
}
let urls=[];
globalThis.fetch=async url=>{urls.push(url);return response({results:[{uid:listing,title:'Rock'}],cursors:{next:'next'}});};
let r=await fabRequest({action:'search',params:{query:'rock & moss',cursor:'page+2'}});
assert.equal(r.data.items[0].uid,listing);assert.equal(r.data.cursor,'next');
assert.match(urls[0],/q=rock\+%26\+moss/);assert.match(urls[0],/cursor=page%2B2/);
for(const [status,expected] of [[401,'AUTH_REQUIRED'],[403,'ACCESS_DENIED'],[429,'RATE_LIMITED']]){
  globalThis.fetch=async()=>response({},status);
  r=await fabRequest({action:'files',params});assert.equal(r.error,expected);
}
globalThis.fetch=async()=>response({},200,'text/html');
assert.equal((await fabRequest({action:'files',params})).error,'SCHEMA_CHANGED');
globalThis.fetch=async()=>response({acquired:false});
assert.equal((await fabRequest({action:'download',params})).error,'NOT_OWNED');
let requested=0;
globalThis.fetch=async url=>{
  if(url.includes('listings-states'))return response({acquired:true});
  if(url.endsWith('/fbx'))return response({files:[{uid:file,name:params.name,size:100,status:'ready'}]});
  requested++;return response({downloadInfo:[{type:'binary',downloadUrl:'https://content-download-emp.distro.on.epicgames.com/file.zip?secret=fixture',expires:new Date(Date.now()+(requested===1?-1000:120000)).toISOString()}]});
};
r=await fabRequest({action:'download',params});assert.equal(r.ok,true);assert.equal(requested,2);
globalThis.fetch=async url=>{
  if(url.includes('listings-states'))return response({acquired:true});
  if(url.endsWith('/fbx'))return response({files:[{uid:file,name:params.name,size:100,status:'ready'}]});
  return response({downloadInfo:[{type:'binary',downloadUrl:'https://content-download-emp.distro.on.epicgames.com/file.zip',expires:'2000-01-01'}]});
};
assert.equal((await fabRequest({action:'download',params})).error,'EXPIRED_URL');
console.log('PASS: search encoding/paging, ownership, 401/403/429, schema, expired URL refresh and failure');
