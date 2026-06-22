import math, time
import numpy as np
from scipy.spatial import cKDTree
from scipy.optimize import minimize
import analyze

SIZES = [analyze.SMALL, analyze.MEDIUM, analyze.LARGE, analyze.XL]  # 70,84,100.8,120.96

# precompute the local surface cloud + cap mesh once per size
_CLOUD = {s: analyze.surface_samples(s) for s in SIZES}
_CV, _CT = analyze.cap_mesh()

# fibonacci dirs (fixed)
_NDIR = 16000
_i = np.arange(_NDIR) + 0.5
_phi = np.arccos(1 - 2*_i/_NDIR)
_gold = math.pi*(1+5**0.5)
_th = _gold*_i
_D = np.column_stack((np.sin(_phi)*np.cos(_th), np.sin(_phi)*np.sin(_th), np.cos(_phi)))


def evaluate(scale_for):
    pl = analyze.build_placements(scale_for)
    clouds=[]; capw=[]; cents=[]; sls=[]
    for (M,sl,sc) in pl:
        R=M[:3,:3]; T=M[:3,3]
        clouds.append((R@(sc*_CLOUD[sl]).T).T + T)
        capw.append((R@(sc*_CV).T).T + T)
        cents.append(clouds[-1].mean(0)); sls.append(int(sl))
    cents=np.array(cents); cdir=cents/np.linalg.norm(cents,axis=1,keepdims=True)
    n=len(clouds)
    # clearance via KDTree on near pairs
    trees=[cKDTree(c) for c in clouds]
    best=1e9; bp=None
    coslim=math.cos(math.radians(75))
    for a in range(n):
        for b in range(a+1,n):
            if cdir[a]@cdir[b] < coslim: continue
            d,_=trees[b].query(clouds[a], k=1)
            m=d.min()
            if m<best: best=m; bp=(sls[a],sls[b])
    # coverage (ray-triangle), cap meshes
    covered=np.zeros(_NDIR,dtype=bool); eps=1e-9
    for w in capw:
        cen=w.mean(0); cdr=cen/np.linalg.norm(cen)
        wn=w/np.linalg.norm(w,axis=1,keepdims=True)
        cosr=(wn@cdr).min()-0.02
        cand=(_D@cdr)>=cosr
        if not cand.any(): continue
        Dc=_D[cand]; hit=np.zeros(len(Dc),dtype=bool)
        for tri in _CT:
            v0,v1,v2=w[tri[0]],w[tri[1]],w[tri[2]]
            e1=v1-v0; e2=v2-v0
            pv=np.cross(Dc,e2); det=pv@e1; ok=np.abs(det)>eps
            inv=np.where(ok,1.0/np.where(ok,det,1),0.0)
            tv=-v0; u=(pv@tv)*inv; qv=np.cross(tv,e1)
            v=(Dc@qv)*inv; t=(e2@qv)*inv
            hit|=ok&(u>=-1e-6)&(v>=-1e-6)&(u+v<=1+1e-6)&(t>0)
        idx=np.where(cand)[0]; covered[idx[hit]]=True
    leak=(~covered).sum()/_NDIR
    return leak, best, bp


TARGET=0.8
def cost(x):
    x=np.clip(x,0.45,1.25)
    m={SIZES[0]:x[0],SIZES[1]:x[1],SIZES[2]:x[2],SIZES[3]:x[3]}
    leak,clr,_=evaluate(lambda sl:m[sl])
    c = 200*leak + max(0,TARGET-clr)*20 - 0.2*min(clr,2.0)
    return c, leak, clr

def cost_only(x):
    return cost(x)[0]

if __name__=="__main__":
    starts=[[0.7,0.7,0.7,0.8],[0.85,0.65,0.7,0.9],[0.9,0.6,0.65,0.95],[0.75,0.75,0.75,0.75]]
    best=None
    for s0 in starts:
        t=time.time()
        res=minimize(cost_only,s0,method='Nelder-Mead',
                     options={'maxiter':70,'xatol':0.01,'fatol':0.05})
        x=np.clip(res.x,0.45,1.25)
        c,leak,clr=cost(x)
        print(f"start {s0} -> scales {np.round(x,3).tolist()}  leak={leak*100:.2f}%  clr={clr:.2f}mm  cost={c:.2f}  ({time.time()-t:.0f}s)")
        if best is None or c<best[0]: best=(c,x,leak,clr)
    print("\nBEST:", np.round(best[1],3).tolist(), f"leak={best[2]*100:.2f}% clr={best[3]:.2f}mm")
