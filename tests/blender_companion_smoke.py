"""blender --background --factory-startup --python-exit-code 1 --python tests/blender_companion_smoke.py [-- downloaded.zip]
Generates a local FBX fixture if no user-owned ZIP is supplied. Does not save preferences.
"""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import time
import urllib.request
import zipfile
import bpy
import addon_utils

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent))
addon_utils.enable(ROOT.name, default_set=True, persistent=False)
from ATBridge.companion import blender_ui as ui
from ATBridge.companion.bridge import Bridge

# Keep the smoke isolated from a user's existing add-on instance on the
# development port while still exercising Blender's real operator path.
ui.Bridge = lambda downloads, cache: Bridge(downloads, cache, port=0)

with tempfile.TemporaryDirectory(prefix='atbridge-test-') as temp:
    root = Path(temp).resolve()
    supplied = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    if supplied:
        archive = Path(supplied[0]).resolve()
    else:
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        bpy.ops.mesh.primitive_cube_add()
        fbx = root/'fixture_low.fbx'
        bpy.ops.export_scene.fbx(filepath=str(fbx), use_selection=True)
        archive = root/'fixture_low.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            z.write(fbx, fbx.name)
            z.writestr('fixture.json', json.dumps({'id':'fixture','name':'Fixture','categories':['3d'],
                'models':[{'uri':'tier_%s/fixture.fbx'%i} for i in range(4)], 'maps':[]}))
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    props = bpy.context.window_manager.atb_companion
    downloads = root/'downloads';downloads.mkdir()
    props.downloads = str(downloads)
    cache = root/'cache';cache.mkdir()
    bpy.context.preferences.addons[ROOT.name].preferences.fab_assets_path = str(cache)
    assert bpy.ops.atb.companion(action='start') == {'FINISHED'}
    def post(path, body=None, token=None):
        req = urllib.request.Request('http://127.0.0.1:%d%s' % (ui._service.port, path), data=json.dumps(body or {}).encode(),
            headers={'Origin':'chrome-extension://'+'a'*32,'Authorization':'Bearer '+(token if token is not None else ui._service.token),
                     'Content-Type':'application/json'})
        with urllib.request.urlopen(req) as result: return json.load(result)
    try:
        # Exercise the real Blender operator used by the approval button, then
        # verify the browser's unauthenticated ticket receives the issued token.
        pair = post('/pair/request', token='')
        assert pair['state'] == 'pending'
        pending = ui._service.pairing_snapshot()
        assert pending['state'] == 'pending' and pending['code'] == pair['code']
        assert bpy.ops.atb.companion(action='approve', request_id=pending['id']) == {'FINISHED'}
        approved = post('/pair/status', {'ticket': pair['ticket']}, token='')
        assert approved['state'] == 'approved'
        assert approved['token'] == ui._service.token
        assert post('/hello', token=approved['token'])['protocol'] == 1
        assert bpy.ops.atb.companion(action='search') == {'FINISHED'}
        job = post('/poll')['job']
        listing = 'f186c225-178a-482b-a122-5508a318a4f0'
        file = 'f0828f52-7f32-4f37-b066-c233568e7659'
        post('/result', {'id':job['id'], 'data':{'items':[{'uid':listing,'title':'Fixture'}]}})
        ui._pump()
        assert len(props.results) == 1
        assert bpy.ops.atb.companion(action='files') == {'FINISHED'}
        job=post('/poll')['job']
        post('/result', {'id':job['id'],'data':{'owned':True,'files':[{'uid':file,'name':archive.name,'size':archive.stat().st_size}]}})
        ui._pump()
        assert bpy.ops.atb.companion(action='download') == {'FINISHED'}
        job=post('/poll')['job']
        target=downloads/'ATBridge'/job['id']/archive.name;target.parent.mkdir(parents=True)
        shutil.copyfile(archive,target)
        post('/result', {'id':job['id'],'data':{'path':str(target)}})
        deadline=time.monotonic()+5
        while ui._service.snapshot(job['id'])['status']=='transferring' and time.monotonic()<deadline:
            time.sleep(0.01)
        assert ui._service.snapshot(job['id'])['status']=='done'
        ui._pump()
        assert Path(ui._ready).is_file()
        ready_a = Path(ui._ready)
        assert bpy.ops.atb.companion(action='import') == {'FINISHED'}
        assert ui._ready == ''
        meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
        assert len(meshes)==1, 'Duplicate model import: %d'%len(meshes)
        if supplied:
            material=meshes[0].active_material
            images=[n.image for n in material.node_tree.nodes if n.type=='TEX_IMAGE']
            assert len(images)==4 and all(tuple(i.size)==(1024,1024) for i in images)

        # A previously ready asset must not survive a newer failed or cancelled download.
        ui._ready = str(ready_a)
        assert bpy.ops.atb.companion(action='download') == {'FINISHED'}
        failed = post('/poll')['job']
        assert ui._ready == ''
        post('/result', {'id':failed['id'],'error':'DOWNLOAD_FAILED'})
        ui._pump()
        assert ui._ready == ''
        try:
            outcome = bpy.ops.atb.companion(action='import')
        except RuntimeError as error:
            assert 'No verified download ready' in str(error)
        else:
            assert outcome == {'CANCELLED'}

        ui._ready = str(ready_a)
        assert bpy.ops.atb.companion(action='download') == {'FINISHED'}
        cancelled = post('/poll')['job']
        assert ui._ready == ''
        assert bpy.ops.atb.companion(action='cancel') == {'FINISHED'}
        ui._pump()
        assert ui._ready == ''
        assert ui._service.snapshot(cancelled['id'])['status'] == 'cancelled'
        try:
            outcome = bpy.ops.atb.companion(action='import')
        except RuntimeError as error:
            assert 'No verified download ready' in str(error)
        else:
            assert outcome == {'CANCELLED'}

        assert bpy.ops.atb.companion(action='search') == {'FINISHED'}
        job=post('/poll')['job'];post('/result',{'id':job['id'],'error':'AUTH_REQUIRED'});ui._pump()
        assert 'AUTH_REQUIRED' in ui._status
        print('PASS: Blender approval operator, HTTP search/files/download handoff, import exactly 1 mesh, auth-expired UI')
    finally:
        ui.shutdown()
addon_utils.disable(ROOT.name,default_set=True)
assert not bpy.app.timers.is_registered(ui._pump)
print('PASS: lifecycle shutdown, no companion service remains')
