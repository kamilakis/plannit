"""Intake: read a room-scan GLB (e.g. a phone LiDAR scan) into named objects of triangles, stdlib only.
load(path) -> [{'name', 'tris': [(p0, p1, p2), …], 'mats': [baseColor or None per primitive]}], glTF frame (Y up).
The starting point for a new project's existing.py; each scan's own quirks (duplicate or bogus objects) are the
project's business (a filter in the project's scan/)."""
import json,struct
CT={5126:('f',4),5125:('I',4),5123:('H',2),5121:('B',1)}
def load(path):
    d=open(path,'rb').read()
    jl=struct.unpack('<I',d[12:16])[0]; j=json.loads(d[20:20+jl]); b0=20+jl+8
    bv=j['bufferViews'];acc=j['accessors']
    def read(ai):
        a=acc[ai];v=bv[a['bufferView']];n={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[a['type']];f,s=CT[a['componentType']]
        st=v.get('byteStride',s*n);o=b0+v.get('byteOffset',0)+a.get('byteOffset',0)
        return [struct.unpack_from('<'+f*n,d,o+i*st) for i in range(a['count'])]
    objs=[]
    for nd in j['nodes']:
        if 'mesh' not in nd: continue
        tris=[];cols=[]
        for p in j['meshes'][nd['mesh']]['primitives']:
            pos=read(p['attributes']['POSITION'])
            idx=[x[0] for x in read(p['indices'])] if 'indices' in p else list(range(len(pos)))
            mat=j['materials'][p['material']] if 'material' in p else {}
            bc=mat.get('pbrMetallicRoughness',{}).get('baseColorFactor')
            for t in range(0,len(idx)-2,3):
                tris.append((pos[idx[t]],pos[idx[t+1]],pos[idx[t+2]]))
            cols.append(bc)
        objs.append({'name':nd.get('name',''),'tris':tris,'mats':cols})
    return objs
