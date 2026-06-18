#!/usr/bin/env python3
"""БАФФЕТ vs ДАЛІО v2 — 13 min | 1280×536 | 24fps | glitch+VHS+audio"""
import math, os as _os, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import imageio_ffmpeg
from cinematic import (
    Timeline, render, make_ken_burns,
    grade_netflix, ease_in_out, ease_out,
    FONT_SANS, FONT_SANS_BOLD, FONT_SERIF_IT,
)

W, H  = 1280, 536
FPS   = 24
SR    = 44100
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_TMP  = _os.path.join(_HERE, "_tmp_novid.mp4")
_WAV  = _os.path.join(_HERE, "_tmp_audio.wav")
OUTPUT= _os.path.join(_HERE, "bvd_v2.mp4")

PHOTO_B = _os.path.join(_HERE, "photo_buffett.webp")
PHOTO_D = _os.path.join(_HERE, "photo_dalio.webp")
if not _os.path.exists(PHOTO_D):
    PHOTO_D = _os.path.join(_HERE, "photo_2.webp")
HAS_B = _os.path.exists(PHOTO_B)
HAS_D = _os.path.exists(PHOTO_D)

CB  = ( 74, 144, 232)
CD  = (232,  90,  74)
BG  = (  6,   6,  10)
TXT = (240, 235, 220)
DIM = (100,  95,  88)
GRN = ( 65, 210, 100)
RED = (220,  55,  55)
YLW = (230, 192,  50)

_rng  = np.random.default_rng(99)
GRAIN = _rng.normal(0, 1.0, (H, W, 3)).astype(np.float32)
_y, _x = np.mgrid[0:H, 0:W]
VIG = np.clip(
    1.0-(np.sqrt(((_x-W/2)/(W/2))**2+((_y-H/2)/(H/2)*1.15)**2)-0.42)*1.9,
    0.16,1.0).astype(np.float32)

def ease(t):
    t=max(0.,min(1.,t)); return t*t*(3-2*t)

def _lf(p,s):
    try: return ImageFont.truetype(p,s)
    except: return ImageFont.load_default()

def _vfx(arr,g=5.5):
    a=arr.astype(np.float32)
    a=np.clip(a+GRAIN*g,0,255)
    a[:,:,0]*=VIG; a[:,:,1]*=VIG; a[:,:,2]*=VIG
    return np.clip(a,0,255).astype(np.uint8)

def _paste(base,ov,x,y,alpha=1.0):
    sh,sw=ov.shape[:2]
    x1,y1=max(x,0),max(y,0); x2,y2=min(x+sw,W),min(y+sh,H)
    if x1>=x2 or y1>=y2: return
    sx,sy=x1-x,y1-y
    a=ov[sy:sy+(y2-y1),sx:sx+(x2-x1),3:4].astype(np.float32)/255.0*alpha
    base[y1:y2,x1:x2]=base[y1:y2,x1:x2]*(1-a)+ov[sy:sy+(y2-y1),sx:sx+(x2-x1),:3].astype(np.float32)*a

_sc={}
def _strip(text,font,color=TXT):
    key=(text,id(font),color)
    if key in _sc: return _sc[key]
    d=ImageDraw.Draw(Image.new("L",(1,1)))
    bb=d.textbbox((0,0),text,font=font)
    tw,th=bb[2]-bb[0],bb[3]-bb[1]
    img=Image.new("RGBA",(tw+8,th+8),(0,0,0,0))
    d2=ImageDraw.Draw(img)
    d2.text((4,4),text,font=font,fill=(0,0,0,155))
    d2.text((2,2),text,font=font,fill=(*color,255))
    s=np.array(img); _sc[key]=s; return s


# ════════ VISUAL FX ════════════════════════════════════════════

def glitch(arr, intensity=1.0, seed=0):
    rng2=np.random.default_rng(seed)
    r=arr.copy().astype(np.float32)
    sr_=int(rng2.integers(4,14)*intensity)
    sb_=-int(rng2.integers(3,9)*intensity)
    r[:,:,0]=np.roll(r[:,:,0],sr_,axis=1)
    r[:,:,2]=np.roll(r[:,:,2],sb_,axis=1)
    for _ in range(int(rng2.integers(3,12)*intensity)):
        y=int(rng2.integers(0,H))
        wx=int(rng2.integers(20,220))
        x0=int(rng2.integers(0,max(1,W-wx)))
        r[y,x0:x0+wx]=np.roll(r[y,x0:x0+wx],int(rng2.integers(-55,55)),axis=0)
    r=np.clip(r*(1.0+rng2.uniform(-0.12,0.35)*intensity),0,255)
    return r.astype(np.uint8)

def vhs(arr, t=0.0):
    r=arr.astype(np.float32)
    sc=np.ones((H,1,1),dtype=np.float32); sc[::2]=0.78; r*=sc
    r[:,:,0]=np.clip(r[:,:,0]*0.62+np.roll(r[:,:,0],4,axis=1)*0.38,0,255)
    noise=np.random.default_rng(int(t*100)%9999).normal(0,11,(H,W,1)).astype(np.float32)
    r=np.clip(r+noise,0,255)
    r[:,:,0]=np.clip(r[:,:,0]*1.06,0,255)
    r[:,:,2]=np.clip(r[:,:,2]*0.88,0,255)
    return r.astype(np.uint8)

def zpunch(arr, scale=1.12, cx=None, cy=None):
    if scale<=1.0: return arr
    cx=cx or W//2; cy=cy or H//2
    nw=int(W/scale); nh=int(H/scale)
    x1=max(0,min(W-nw,cx-nw//2)); y1=max(0,min(H-nh,cy-nh//2))
    return np.array(Image.fromarray(arr[y1:y1+nh,x1:x1+nw]).resize((W,H),Image.LANCZOS))

def mblur(arr, r=5):
    return np.array(Image.fromarray(arr).filter(ImageFilter.GaussianBlur(radius=r)))

def desat(arr, amt=0.75):
    g=(arr[:,:,0]*0.299+arr[:,:,1]*0.587+arr[:,:,2]*0.114)
    g3=np.stack([g,g,g],2)
    return np.clip(arr.astype(np.float32)*(1-amt)+g3*amt,0,255).astype(np.uint8)


# ════════ AUDIO ════════════════════════════════════════════════

def _thud(dur=0.35,freq=44,decay=9.0):
    n=int(SR*dur); t=np.linspace(0,dur,n)
    env=np.exp(-t*decay)
    fd=freq*(1+0.6*np.exp(-t*18))
    ph=np.cumsum(2*np.pi*fd/SR)
    return np.sin(ph)*env*0.9

def _whoosh(dur=0.45):
    n=int(SR*dur); t=np.linspace(0,1,n)
    noise=np.random.default_rng(1).normal(0,1,n)
    k=30; noise=np.convolve(noise,np.ones(k)/k,'same')
    env=np.sin(np.pi*t)**1.2*0.55
    return noise*env

def _glitch_snd(dur=0.09):
    n=int(SR*dur)
    rng_g=np.random.default_rng(7)
    s=rng_g.choice([-1.0,0.0,1.0],n)*rng_g.uniform(0.2,1.0,n)
    env=np.exp(-np.linspace(0,12,n))
    return s*env*0.55

def _drone(dur,freq=42):
    n=int(SR*dur); t=np.linspace(0,dur,n)
    w=(np.sin(2*np.pi*freq*t)*0.35+
       np.sin(2*np.pi*freq*1.5*t)*0.18+
       np.sin(2*np.pi*freq*2*t)*0.10)
    w*=1.0+0.12*np.sin(2*np.pi*0.22*t)
    fade=min(int(SR*0.6),n//4)
    w[:fade]*=np.linspace(0,1,fade); w[-fade:]*=np.linspace(1,0,fade)
    return w*0.4

def _riser(dur,f0=30,f1=90):
    n=int(SR*dur); t=np.linspace(0,dur,n)
    fr=np.linspace(f0,f1,n)
    ph=np.cumsum(2*np.pi*fr/SR)
    env=np.linspace(0,1,n)**2
    noise=np.random.default_rng(5).normal(0,0.08,n)
    return (np.sin(ph)*0.4+noise)*env*0.6

def _chord(dur=0.7):
    n=int(SR*dur); t=np.linspace(0,dur,n)
    env=np.exp(-t*4.5)
    w=(np.sin(2*np.pi*55*t)*0.5+
       np.sin(2*np.pi*82*t)*0.3+
       np.sin(2*np.pi*110*t)*0.2)
    return w*env*0.85

def place(audio,snd,ts,vol=1.0):
    idx=int(ts*SR); m=len(snd); end=min(idx+m,len(audio)); na=end-idx
    if na<=0: return
    s=(snd[:na]*vol).astype(np.float32)
    audio[idx:end,0]+=s; audio[idx:end,1]+=s

def build_audio(total, events):
    n=int(SR*total)+SR
    audio=np.zeros((n,2),dtype=np.float32)
    for (ts,snd,vol) in events: place(audio,snd,ts,vol)
    audio=np.tanh(audio*0.8)*1.1
    pk=np.max(np.abs(audio))
    if pk>0.9: audio=audio/pk*0.9
    return audio[:int(SR*total)]

def save_wav(audio,path):
    ai=np.clip(audio*32767,-32767,32767).astype(np.int16)
    with wave.open(path,'w') as wf:
        wf.setnchannels(2); wf.setsampwidth(2)
        wf.setframerate(SR); wf.writeframes(ai.tobytes())

def mux(vpath,apath,opath):
    ff=imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ff,'-y','-i',vpath,'-i',apath,
                    '-c:v','copy','-c:a','aac','-b:a','160k',
                    '-shortest',opath],check=True,capture_output=True)
    print(f"✓ {opath}")


# ════════ SCENE BUILDERS ═══════════════════════════════════════

def slam_text(items, duration, bg=BG, accent=None, glitch_at=None):
    """
    Items: [(text, color, size, appear_at), ...]
    Text SLAMS in from top with motion blur, then settles.
    glitch_at: time to apply glitch effect (optional).
    """
    fc={}
    def _font(sz):
        if sz not in fc: fc[sz]=_lf(FONT_SANS_BOLD,sz)
        return fc[sz]

    strips=[]; total_h=sum(sz+int(sz*0.38) for (_,_,sz,_) in items)
    y=(H-total_h)//2
    for (txt,col,sz,at) in items:
        s=_strip(txt,_font(sz),color=col)
        sx=(W-s.shape[1])//2
        strips.append((s,sx,y,at)); y+=sz+int(sz*0.38)

    def frame(t):
        base=np.full((H,W,3),bg,dtype=np.float32)
        if accent:
            base[0:5]=np.array(accent,dtype=np.float32)
            base[H-5:H]=np.array(accent,dtype=np.float32)

        for (s,sx,sy,at) in strips:
            age=t-at
            if age<-0.08: continue
            t_in=ease(min(max(age/0.22,0),1.0))
            # Slam: comes from above with overshoot
            overshoot=math.sin(max(0,t_in)*math.pi)*0.08*(1-t_in)
            yoff=int((1-t_in)*-60)+int(overshoot*20)
            blur_r=max(0,int((1-t_in)*8))
            if blur_r>0:
                sc=Image.fromarray(s)
                sc=sc.filter(ImageFilter.GaussianBlur(radius=blur_r))
                s2=np.array(sc)
            else:
                s2=s
            _paste(base,s2,sx,sy+yoff,alpha=t_in)

        if glitch_at and abs(t-glitch_at)<0.12:
            base=glitch(np.clip(base,0,255).astype(np.uint8),
                        intensity=1.5,seed=int(t*100)).astype(np.float32)

        fi=ease(min(t/0.4,1.0)); fo=ease(min((duration-t)/0.45,1.0))
        base*=min(fi,fo)
        return _vfx(base,g=4.0)

    return frame


def act_header(act_num, title, color, duration=6.0):
    """Dramatic act title card — black with colored accent line."""
    f_act=_lf(FONT_SANS_BOLD,15)
    f_tit=_lf(FONT_SANS_BOLD,54)

    s_act=_strip(f"АКТ {act_num}",f_act,color=color)
    s_tit=_strip(title,f_tit,color=TXT)

    def frame(t):
        base=np.full((H,W,3),(4,4,8),dtype=np.float32)
        # Horizontal accent line
        p=ease(min(t/0.5,1.0))
        lw=int(W*p)
        base[H//2-2:H//2+2,:lw]=np.array(color,dtype=np.float32)

        p2=ease(min(max((t-0.35)/0.5,0),1.0))
        if p2>0.01:
            yoff=int((1-p2)*30)
            _paste(base,s_act,(W-s_act.shape[1])//2,H//2-75+yoff,alpha=p2)
        p3=ease(min(max((t-0.6)/0.5,0),1.0))
        if p3>0.01:
            yoff=int((1-p3)*25)
            _paste(base,s_tit,(W-s_tit.shape[1])//2,H//2-5+yoff,alpha=p3)

        fi=ease(min(t/0.4,1.0)); fo=ease(min((duration-t)/0.5,1.0))
        base*=min(fi,fo)
        return _vfx(base,g=3.5)

    return frame


def split_vs(duration):
    if HAS_B:
        kb_b=make_ken_burns(PHOTO_B,duration,W,H,1.0,1.06,(0.5,0.5),(0.52,0.5),"netflix",0.3,0.3)
    if HAS_D:
        kb_d=make_ken_burns(PHOTO_D,duration,W,H,1.0,1.06,(0.5,0.5),(0.48,0.5),"netflix",0.3,0.3)

    f_name=_lf(FONT_SANS_BOLD,22); f_sub=_lf(FONT_SANS,14); f_vs=_lf(FONT_SANS_BOLD,84)

    def _side(t,is_left):
        col=CB if is_left else CD
        if is_left and HAS_B: arr=kb_b(t).astype(np.float32)
        elif not is_left and HAS_D: arr=kb_d(t).astype(np.float32)
        else:
            arr=np.full((H,W,3),BG,dtype=np.float32)
            cx=W//4 if is_left else 3*W//4
            dist=np.sqrt(((_x-cx)/(W*0.28))**2+((_y-H//2)/(H*0.5))**2)
            g=np.clip(1.0-dist*1.3,0,1)**1.5*0.4
            arr[:,:,0]+=g*col[0]; arr[:,:,1]+=g*col[1]; arr[:,:,2]+=g*col[2]
        tint=np.array(col,dtype=np.float32)*0.16
        return np.clip(arr*0.84+tint[np.newaxis,np.newaxis,:],0,255)

    def frame(t):
        left=_side(t,True); right=_side(t,False)
        result=np.empty((H,W,3),dtype=np.float32)
        result[:,:W//2]=left[:,:W//2]; result[:,W//2:]=right[:,W//2:]
        # Crack divider (two pixels, color shift)
        result[:,W//2-1:W//2+1]=180

        img=Image.fromarray(np.clip(result,0,255).astype(np.uint8))
        d=ImageDraw.Draw(img)

        vp=ease(min(max((t-0.5)/0.4,0),1.0))
        if vp>0.01:
            pulse=1.0+0.05*math.sin(t*math.pi*2.5)
            fvs=_lf(FONT_SANS_BOLD,int(84*vp*pulse))
            vsb=d.textbbox((0,0),"VS",font=fvs)
            vw,vh=vsb[2]-vsb[0],vsb[3]-vsb[1]
            vx=(W-vw)//2; vy=(H-vh)//2-8
            d.ellipse([vx-34,vy-16,vx+vw+34,vy+vh+16],fill=(6,6,14))
            d.ellipse([vx-32,vy-14,vx+vw+32,vy+vh+14],outline=(180,160,80),width=2)
            d.text((vx+3,vy+3),"VS",font=fvs,fill=(0,0,0,180))
            d.text((vx,vy),"VS",font=fvs,fill=(235,220,185))

        np_=ease(min(max((t-0.3)/0.5,0),1.0))
        if np_>0.01:
            yoff=int((1-np_)*22)
            for (nm,sb,col,bx) in [
                ("WARREN BUFFETT","Berkshire Hathaway",CB,0),
                ("RAY DALIO","Bridgewater Associates",CD,W//2),
            ]:
                ny=int(H*0.82)+yoff
                nb=d.textbbox((0,0),nm,font=f_name); nw=nb[2]-nb[0]
                nx=bx+(W//2-nw)//2
                d.rectangle([bx+20,ny-9,bx+W//2-20,ny-5],fill=col)
                d.text((nx+2,ny+2),nm,font=f_name,fill=(0,0,0))
                d.text((nx,ny),nm,font=f_name,fill=col)
                sbb=d.textbbox((0,0),sb,font=f_sub); sw=sbb[2]-sbb[0]
                d.text((bx+(W//2-sw)//2,ny+30),sb,font=f_sub,fill=DIM)

        result=np.array(img).astype(np.float32)
        result=np.clip(result+GRAIN*5.5,0,255)
        fi=ease(min(t/0.5,1.0)); fo=ease(min((duration-t)/0.5,1.0))
        return np.clip(result*min(fi,fo),0,255).astype(np.uint8)

    return frame


def profile_scene(photo,name,role,color,captions,duration,
                  zoom_s=1.0,zoom_e=1.07,pan_s=(0.5,0.5),pan_e=(0.5,0.5),
                  do_vhs=False):
    has_p=photo and _os.path.exists(photo)
    if has_p:
        kb=make_ken_burns(photo,duration,W,H,zoom_s,zoom_e,pan_s,pan_e,"netflix",0.5,0.5)

    f_name=_lf(FONT_SANS_BOLD,26); f_role=_lf(FONT_SANS,16); f_cap=_lf(FONT_SANS,28)

    cap_data=[]
    dummy_d=ImageDraw.Draw(Image.new("L",(1,1)))
    for (cs,ce,txt) in captions:
        words=txt.split(); lines,cur=[],""
        for w in words:
            test=(cur+" "+w).strip()
            bb=dummy_d.textbbox((0,0),test,font=f_cap)
            if bb[2]-bb[0]<=int(W*0.78): cur=test
            else:
                if cur: lines.append(cur)
                cur=w
        if cur: lines.append(cur)
        lh=36; sh=len(lines)*lh+22
        img_c=Image.new("RGBA",(W,sh),(0,0,0,0))
        dc=ImageDraw.Draw(img_c)
        for i,ln in enumerate(lines):
            lb=dc.textbbox((0,0),ln,font=f_cap); lw=lb[2]-lb[0]
            lx=(W-lw)//2; ly=i*lh+11
            dc.text((lx+2,ly+2),ln,font=f_cap,fill=(0,0,0,155))
            dc.text((lx,ly),ln,font=f_cap,fill=(242,237,224,255))
        cap_data.append((np.array(img_c),cs,ce,sh))

    def _proc_bg(t):
        arr=np.full((H,W,3),BG,dtype=np.float32)
        dist=np.sqrt(((_x-W//2)/(W*0.55))**2+((_y-H//2)/(H*0.65))**2)
        glow=np.clip(1.0-dist*1.3,0,1)**2*(0.22+0.05*math.sin(t*0.8))
        arr[:,:,0]+=glow*color[0]*0.55; arr[:,:,1]+=glow*color[1]*0.55; arr[:,:,2]+=glow*color[2]*0.55
        return np.clip(arr,0,255).astype(np.uint8)

    def frame(t):
        if has_p: base=kb(t).astype(np.float32)
        else: base=_proc_bg(t).astype(np.float32)

        lt_p=ease(min(max((t-0.6)/0.5,0),1.0))
        if lt_p>0.01:
            ylt=int(H*0.79+(1-lt_p)*28); bh=52
            y1=max(0,ylt); y2=min(H,ylt+bh)
            if y1<y2:
                bar=np.zeros((y2-y1,W,3),dtype=np.float32)
                bar[:]=np.array([10,10,16],dtype=np.float32)
                bar[:,:6]=np.array(color,dtype=np.float32)
                base[y1:y2]=base[y1:y2]*(1-0.80*lt_p)+bar*(0.80*lt_p)
            img_tmp=Image.fromarray(np.clip(base,0,255).astype(np.uint8))
            dlt=ImageDraw.Draw(img_tmp)
            dlt.text((24,ylt+5+2),name,font=f_name,fill=(0,0,0,200))
            dlt.text((24,ylt+5),name,font=f_name,fill=color)
            dlt.text((24,ylt+35),role,font=f_role,fill=DIM)
            base=np.array(img_tmp).astype(np.float32)

        for (cs_arr,cs,ce,sh) in cap_data:
            if cs<=t<=ce:
                fi2=ease(min((t-cs)/0.38,1.0)); fo2=ease(min((ce-t)/0.38,1.0))
                a=min(fi2,fo2); yc=H-sh-24
                base[max(0,yc-10):min(H,yc+sh+10)]=(
                    base[max(0,yc-10):min(H,yc+sh+10)]*0.22+
                    np.array([8,8,14],dtype=np.float32)*0.78)
                _paste(base,cs_arr,0,yc,alpha=a)
                break

        if do_vhs:
            base=vhs(np.clip(base,0,255).astype(np.uint8),t).astype(np.float32)

        fi=ease(min(t/0.5,1.0)); fo=ease(min((duration-t)/0.5,1.0))
        base*=min(fi,fo)
        return _vfx(base,g=5.5)

    return frame


def impact_stat(value_str,label,sublabel,color,duration,
                prefix="",suffix="",count_to=None):
    f_big=_lf(FONT_SANS_BOLD,108); f_lbl=_lf(FONT_SANS_BOLD,32); f_sub=_lf(FONT_SANS,20)

    def frame(t):
        arr=np.full((H,W,3),BG,dtype=np.float32)
        arr[0:5]=np.array(color,dtype=np.float32)
        img=Image.fromarray(arr.astype(np.uint8)); d=ImageDraw.Draw(img)
        prog=ease(min(t/1.0,1.0))
        val=f"{prefix}{int((count_to or 0)*prog)}{suffix}" if count_to else value_str
        sp=ease(min(t/0.4,1.0))
        vb=d.textbbox((0,0),val,font=f_big); vw=vb[2]-vb[0]
        vx=(W-vw)//2; vy=H//2-80
        d.text((vx+5,vy+5),val,font=f_big,fill=(0,0,0,200))
        d.text((vx,vy),val,font=f_big,fill=(*color,int(255*sp)))
        lb=d.textbbox((0,0),label,font=f_lbl); lx=(W-(lb[2]-lb[0]))//2
        d.text((lx,vy+128),label,font=f_lbl,fill=TXT)
        if sublabel:
            sb=d.textbbox((0,0),sublabel,font=f_sub); sx=(W-(sb[2]-sb[0]))//2
            d.text((sx,vy+172),sublabel,font=f_sub,fill=DIM)
        result=np.array(img).astype(np.float32)
        result=np.clip(result+GRAIN*4.0,0,255)
        result[:,:,0]*=VIG; result[:,:,1]*=VIG; result[:,:,2]*=VIG
        fi=ease(min(t/0.4,1.0)); fo=ease(min((duration-t)/0.45,1.0))
        return np.clip(result*min(fi,fo),0,255).astype(np.uint8)

    return frame


def impact_split(title,vl,ll,cl,vr,lr,cr,duration):
    f_tit=_lf(FONT_SANS_BOLD,28); f_big=_lf(FONT_SANS_BOLD,96); f_lbl=_lf(FONT_SANS_BOLD,26)

    def frame(t):
        arr=np.full((H,W,3),BG,dtype=np.float32)
        arr[0:5]=np.array(cl,dtype=np.float32); arr[H-5:H]=np.array(cr,dtype=np.float32)
        img=Image.fromarray(arr.astype(np.uint8)); d=ImageDraw.Draw(img)
        tb=d.textbbox((0,0),title,font=f_tit); tx=(W-(tb[2]-tb[0]))//2
        d.text((tx+2,22),title,font=f_tit,fill=(0,0,0,160))
        d.text((tx,20),title,font=f_tit,fill=TXT)
        d.line([W//2,68,W//2,H-20],fill=(40,40,55),width=1)
        fl=ease(min(max((t-0.3)/0.45,0),1.0)); fr=ease(min(max((t-0.7)/0.45,0),1.0))
        for (val,lbl,col,bx,fi2) in [(vl,ll,cl,0,fl),(vr,lr,cr,W//2,fr)]:
            vb=d.textbbox((0,0),val,font=f_big); vw=vb[2]-vb[0]
            vx=bx+(W//2-vw)//2; vy=H//2-75
            d.text((vx+4,vy+4),val,font=f_big,fill=(0,0,0,180))
            d.text((vx,vy),val,font=f_big,fill=(*col,int(255*fi2)))
            lb=d.textbbox((0,0),lbl,font=f_lbl); lx=bx+(W//2-(lb[2]-lb[0]))//2
            d.text((lx,vy+115),lbl,font=f_lbl,fill=(*col,int(255*fi2)))
        result=np.array(img).astype(np.float32)
        result=np.clip(result+GRAIN*4.5,0,255)
        result[:,:,0]*=VIG; result[:,:,1]*=VIG; result[:,:,2]*=VIG
        fi=ease(min(t/0.4,1.0)); fo=ease(min((duration-t)/0.5,1.0))
        return np.clip(result*min(fi,fo),0,255).astype(np.uint8)

    return frame


def comparison_table(duration):
    rows=[
        ("Стиль","Концентровано — 5-10 позицій","Диверсифіковано — 15+ класів"),
        ("Логіка","Купуй переконання","Збудуй систему"),
        ("Горизонт","Десятиліття+","Будь-який ринок"),
        ("Ризик","Середній–Вис.","Низький–Серед."),
        ("2008 рік","−25%","+14%"),
        ("30 років","~20%/рік","~7-8%/рік"),
        ("Ідея","Інвестування = мистецтво","Інвестування = інженерія"),
    ]
    ri=(duration-1.5)/len(rows)
    f_h=_lf(FONT_SANS_BOLD,20); f_l=_lf(FONT_SANS,18); f_v=_lf(FONT_SANS_BOLD,20); f_t=_lf(FONT_SANS_BOLD,30)
    XL,XB,XD=52,330,730; RH=46

    def frame(t):
        arr=np.full((H,W,3),BG,dtype=np.float32)
        arr[0:4]=np.array(YLW,dtype=np.float32)
        img=Image.fromarray(arr.astype(np.uint8)); d=ImageDraw.Draw(img)
        d.text((XL,14),"БАФФЕТ  vs  ДАЛІО — ПОРІВНЯННЯ",font=f_t,fill=TXT)
        d.text((XB,56),"БАФФЕТ",font=f_h,fill=CB); d.text((XD,56),"ДАЛІО",font=f_h,fill=CD)
        d.line([40,90,W-40,90],fill=(45,45,58),width=1)
        for i,(lbl,bv,dv) in enumerate(rows):
            at=0.8+i*ri
            if t<at-0.04: continue
            age=t-at; t_in=ease(min(max(age/0.38,0),1.0)); xoff=int((1-t_in)*50)
            ry=100+i*RH
            if i%2==0: d.rectangle([40,ry-4,W-40,ry+RH-6],fill=(14,14,20))
            d.text((XL+xoff,ry),lbl,font=f_l,fill=DIM)
            bc=(GRN if bv.startswith("+") else RED if bv.startswith("−") or bv.startswith("-") else TXT)
            dc=(GRN if dv.startswith("+") else RED if dv.startswith("−") or dv.startswith("-") else TXT)
            d.text((XB+xoff,ry),bv,font=f_v,fill=bc)
            d.text((XD+xoff,ry),dv,font=f_v,fill=dc)
            if i<len(rows)-1: d.line([40,ry+RH-7,W-40,ry+RH-7],fill=(28,28,38),width=1)
        result=np.array(img).astype(np.float32)
        result=np.clip(result+GRAIN*4.0,0,255)
        result[:,:,0]*=VIG; result[:,:,1]*=VIG; result[:,:,2]*=VIG
        fi=ease(min(t/0.5,1.0)); fo=ease(min((duration-t)/0.5,1.0))
        return np.clip(result*min(fi,fo),0,255).astype(np.uint8)

    return frame


def personality_test(duration):
    btraits=["Читаєш 500 стор/тиждень",
             "Любиш вивчати бізнес роками",
             "Чекаєш десятиліттями без паніки",
             "Хочеш BEAT the market",
             "Довіряєш власному аналізу"]
    dtraits=["Хочеш спати спокійно",
             "Не хочеш стежити за ринком",
             "Захист важливіший за прибуток",
             "Хочеш SURVIVE the market",
             "Довіряєш системі > інтуїції"]
    ti=(duration-2.0)/max(len(btraits),1)
    fh=_lf(FONT_SANS_BOLD,26); fs=_lf(FONT_SANS_BOLD,16); ft=_lf(FONT_SANS,21); fq=_lf(FONT_SANS_BOLD,24)

    def frame(t):
        arr=np.full((H,W,3),BG,dtype=np.float32)
        arr[:,:W//2,0]+=6; arr[:,:W//2,2]+=8
        arr[:,W//2:,0]+=10; arr[:,W//2:,2]+=4
        arr[0:4]=np.array(CB,dtype=np.float32); arr[H-4:H]=np.array(CD,dtype=np.float32)
        img=Image.fromarray(np.clip(arr,0,255).astype(np.uint8)); d=ImageDraw.Draw(img)
        d.line([W//2,0,W//2,H],fill=(35,35,50),width=2)
        qp=ease(min(t/0.45,1.0))
        if qp>0.01:
            qt="ХТО ТИ ЗА ТИПОМ ІНВЕСТОРА?"
            qb=d.textbbox((0,0),qt,font=fq)
            d.text(((W-(qb[2]-qb[0]))//2+2,14),qt,font=fq,fill=(0,0,0,160))
            d.text(((W-(qb[2]-qb[0]))//2,12),qt,font=fq,fill=TXT)
        hp=ease(min(max((t-0.4)/0.45,0),1.0))
        if hp>0.01:
            for (nm,col,bx) in [("ТИ — БАФФЕТ, якщо...",CB,0),("ТИ — ДАЛІО, якщо...",CD,W//2)]:
                nb=d.textbbox((0,0),nm,font=fh); nw=nb[2]-nb[0]
                nx=bx+(W//2-nw)//2
                d.rectangle([bx+15,50,bx+W//2-15,53],fill=col)
                d.text((nx,58),nm,font=fh,fill=col)
        for i,(bt,dt) in enumerate(zip(btraits,dtraits)):
            at=1.0+i*ti
            if t<at-0.04: continue
            age=t-at; t_in=ease(min(max(age/0.38,0),1.0))
            yp=108+i*52; xoff=int((1-t_in)*28)
            # Zoom punch on first trait
            # Buffett
            d.text((30+xoff,yp),"▸",font=fs,fill=CB)
            d.text((50+xoff,yp),bt,font=ft,fill=TXT)
            # Dalio
            d.text((W//2+30+xoff,yp),"▸",font=fs,fill=CD)
            d.text((W//2+50+xoff,yp),dt,font=ft,fill=TXT)
        result=np.array(img).astype(np.float32)
        result=np.clip(result+GRAIN*4.0,0,255)
        result[:,:,0]*=VIG; result[:,:,1]*=VIG; result[:,:,2]*=VIG
        fi=ease(min(t/0.5,1.0)); fo=ease(min((duration-t)/0.5,1.0))
        return np.clip(result*min(fi,fo),0,255).astype(np.uint8)

    return frame


def plot_twist(duration):
    """ЗАЧЕКАЙ. ЩО? — zoom punch scene."""
    items1=[
        ("«Сам Баффет рекомендує",TXT,38,0.3),
        ("90% людей купувати...",TXT,38,1.4),
        ("індексний фонд S&P 500.»",YLW,44,2.5),
    ]
    items2=[
        ("ЗАЧЕКАЙ.",TXT,72,4.5),
        ("ЩО?",CD,96,5.4),
    ]
    items3=[
        ("Баффет-стратегія — для Баффета.",CB,34,7.5),
        ("Для всіх інших — Даліо.",CD,34,9.0),
        ("Це найважливіший урок відео.",YLW,30,10.5),
    ]

    fc={}
    def _font(sz):
        if sz not in fc: fc[sz]=_lf(FONT_SANS_BOLD,sz)
        return fc[sz]

    all_items=items1+items2+items3
    total_h=sum(sz+int(sz*0.35) for (_,_,sz,_) in all_items)
    y=(H-total_h)//2
    strips=[]
    for (txt,col,sz,at) in all_items:
        s=_strip(txt,_font(sz),color=col)
        sx=(W-s.shape[1])//2
        strips.append((s,sx,y,at,sz)); y+=sz+int(sz*0.35)

    def frame(t):
        base=np.full((H,W,3),(4,4,8),dtype=np.float32)
        base[0:4]=np.array(YLW,dtype=np.float32)

        for (s,sx,sy,at,sz) in strips:
            age=t-at
            if age<-0.08: continue
            t_in=ease(min(max(age/0.28,0),1.0))
            yoff=int((1-t_in)*30)
            # Zoom punch on "ЩО?"
            if "ЩО?" in _sc and age<0.5 and age>=0:
                pass  # handled below
            _paste(base,s,sx,sy+yoff,alpha=t_in)

        # Glitch at the twist moment
        if 4.4<=t<=4.7:
            gi=ease(min((t-4.4)/0.15,1.0))*ease(min((4.7-t)/0.15,1.0))
            base=glitch(np.clip(base,0,255).astype(np.uint8),
                        intensity=gi*2.2,seed=int(t*200)).astype(np.float32)
        # Zoom punch on "ЩО?"
        if 5.35<=t<=5.8:
            zp=ease(min((t-5.35)/0.25,1.0))*1.18
            base=zpunch(np.clip(base,0,255).astype(np.uint8),scale=zp).astype(np.float32)

        fi=ease(min(t/0.4,1.0)); fo=ease(min((duration-t)/0.5,1.0))
        base*=min(fi,fo)
        return _vfx(base,g=4.0)

    return frame


def cta_scene(duration, is_final=False):
    fq=_lf(FONT_SANS_BOLD,42); fs=_lf(FONT_SANS,24); fh=_lf(FONT_SANS,20)
    q1="Якби тобі дали $10,000 прямо зараз —"
    q2="чий підхід ти б обрав?"
    hint="Пиши: «Я — Баффет» або «Я — Даліо» + ЧОМУ  ↓"
    outro="Дякую. Підписуйся — попереду ще більше битв ідей." if is_final else ""

    def frame(t):
        arr=np.full((H,W,3),BG,dtype=np.float32)
        sweep=(t*0.20)%1.0; cx=int(sweep*W*1.3-W*0.15)
        dist2=np.sqrt(((_x-cx)/(W*0.45))**2+((_y-H//2)/(H*0.6))**2)
        glow=np.clip(1.0-dist2*1.1,0,1)*0.15
        arr[:,:,0]+=glow*CB[0]; arr[:,:,1]+=glow*CB[1]; arr[:,:,2]+=glow*CB[2]
        arr[:,:,0]+=glow*CD[0]*0.5; arr[:,:,1]+=glow*CD[1]*0.5; arr[:,:,2]+=glow*CD[2]*0.5

        img=Image.fromarray(np.clip(arr,0,255).astype(np.uint8)); d=ImageDraw.Draw(img)
        p1=ease(min(max((t-0.4)/0.5,0),1.0))
        p2=ease(min(max((t-0.9)/0.5,0),1.0))
        p3=ease(min(max((t-1.5)/0.5,0),1.0))
        p4=ease(min(max((t-2.5)/0.5,0),1.0)) if is_final else 0

        for (txt,fnt,col,prog,ypos) in [
            (q1,fq,TXT,p1,H//2-85),(q2,fq,TXT,p2,H//2-18),
            (hint,fh,DIM,p3,H//2+65),
        ]:
            if prog<0.01: continue
            tb=d.textbbox((0,0),txt,font=fnt); tw=tb[2]-tb[0]
            tx=(W-tw)//2; yoff=int((1-prog)*20)
            d.text((tx+2,ypos+yoff+2),txt,font=fnt,fill=(0,0,0,int(160*prog)))
            d.text((tx,ypos+yoff),txt,font=fnt,fill=(*col[:3],int(255*prog)))

        if is_final and p4>0.01:
            tb=d.textbbox((0,0),outro,font=fs); tw=tb[2]-tb[0]
            tx=(W-tw)//2; ypos=H//2+115
            d.text((tx,ypos),outro,font=fs,fill=(*YLW,int(255*p4)))

        pulse=(math.sin(t*math.pi*1.8)+1)/2
        bc=tuple(int(c*0.4+c*0.6*pulse) for c in YLW)
        d.rectangle([0,H-5,W,H],fill=bc); d.rectangle([0,0,W,4],fill=bc)

        result=np.array(img).astype(np.float32)
        result=np.clip(result+GRAIN*4.5,0,255)
        result[:,:,0]*=VIG; result[:,:,1]*=VIG; result[:,:,2]*=VIG
        fi=ease(min(t/0.5,1.0)); fo=ease(min((duration-t)/0.5,1.0))
        return np.clip(result*min(fi,fo),0,255).astype(np.uint8)

    return frame


def verdict_scene(duration):
    items=[
        ("Це не битва.", TXT, 52, 0.3),
        ("Це дзеркало.", YLW, 64, 1.5),
        ("", TXT, 8, 2.9),
        ("Баффет = мистецтво вибору.", CB, 34, 3.2),
        ("Даліо = математика захисту.", CD, 34, 4.6),
        ("", TXT, 8, 6.0),
        ("Хто ти, коли ринок падає -40%?", TXT, 32, 6.3),
    ]
    fc={}
    def _font(sz):
        if sz not in fc: fc[sz]=_lf(FONT_SANS_BOLD,sz)
        return fc[sz]
    total_h=sum(sz+int(sz*0.4) for (_,_,sz,_) in items)
    y=(H-total_h)//2; strips=[]
    for (txt,col,sz,at) in items:
        if txt:
            s=_strip(txt,_font(sz),color=col); sx=(W-s.shape[1])//2
            strips.append((s,sx,y,at))
        y+=sz+int(sz*0.4)

    def frame(t):
        base=np.full((H,W,3),(4,4,8),dtype=np.float32)
        # Slow gradient breathing
        alpha_bg=0.12+0.06*math.sin(t*0.4)
        dist=np.sqrt(((_x-W//2)/(W*0.7))**2+((_y-H//2)/(H*0.7))**2)
        glow=np.clip(1.0-dist*1.2,0,1)*alpha_bg
        base[:,:,1]+=glow*40; base[:,:,0]+=glow*20

        for (s,sx,sy,at) in strips:
            age=t-at
            if age<-0.08: continue
            t_in=ease(min(max(age/0.35,0),1.0))
            yoff=int((1-t_in)*25)
            _paste(base,s,sx,sy+yoff,alpha=t_in)

        fi=ease(min(t/0.5,1.0)); fo=ease(min((duration-t)/0.5,1.0))
        base*=min(fi,fo)
        return _vfx(base,g=4.5)

    return frame


# ════════ CAPTIONS ══════════════════════════════════════════════

B_CAPS=[
    (1.0, 9.5, "Він читає 500 сторінок щотижня. Щоб знайти одну компанію."),
    (10.0,19.5,"«Диверсифікація — захист від невігластва.»"),
    (20.0,29.5,"Coca-Cola. Apple. American Express. Він не купує ринок."),
    (30.0,39.5,"Він купує переконання — і тримає десятиліттями."),
]

D_CAPS=[
    (1.0, 9.5, "«Ніхто не може передбачити майбутнє. Навіть я.»"),
    (10.0,19.5,"Замість вгадування переможця — він будує систему."),
    (20.0,29.5,"All Weather: зростання, рецесія, інфляція, дефляція."),
    (30.0,39.5,"Він не вгадує погоду. Він одягається для будь-якої."),
]

CRISIS_CAPS=[
    (1.0, 9.5, "Жовтень 2008. Фінансова система розвалюється."),
    (10.0,19.5,"Баффет: «Buy American. I am.» Купує мільярдами в паніці."),
    (20.0,29.5,"Bridgewater: +14% поки S&P 500 впав -37%."),
    (30.0,37.5,"Один переміг завдяки сміливості. Другий — завдяки структурі."),
]


# ════════ VISUAL INSERTS ═══════════════════════════════════════

def newspaper_insert(headline, subhead, date, source, duration):
    """Aged newspaper clipping — NYT/Bloomberg style."""
    f_src  = _lf(FONT_SANS_BOLD, 13)
    f_date = _lf(FONT_SANS,      12)
    f_head = _lf(FONT_SERIF_IT,  48)
    f_sub  = _lf(FONT_SANS,      20)
    f_body = _lf(FONT_SANS,      15)

    PAPER  = (235, 225, 200)   # aged newsprint
    INK    = ( 22,  18,  12)   # dark ink
    REDINK = (180,  30,  30)

    # Pre-render to PIL
    img = Image.new("RGB", (W, H), (20, 18, 14))
    d   = ImageDraw.Draw(img)

    # Paper rectangle (center)
    px1, py1, px2, py2 = 60, 30, W-60, H-30
    d.rectangle([px1-2, py1-2, px2+2, py2+2], fill=(150, 140, 120))
    d.rectangle([px1, py1, px2, py2], fill=PAPER)

    # Newspaper name header
    d.rectangle([px1, py1, px2, py1+42], fill=INK)
    sb = d.textbbox((0,0), source, font=f_src)
    sw = sb[2]-sb[0]
    d.text(((W-sw)//2, py1+12), source, font=f_src, fill=PAPER)

    # Date line
    d.text((px1+14, py1+48), date, font=f_date, fill=(100,90,75))
    d.line([px1+10, py1+64, px2-10, py1+64], fill=(150,140,120), width=1)
    d.line([px1+10, py1+67, px2-10, py1+67], fill=(150,140,120), width=1)

    # Headline (serif, large)
    # Wrap headline
    words = headline.split()
    lines2, cur = [], ""
    for w in words:
        test = (cur+" "+w).strip()
        bb = d.textbbox((0,0), test, font=f_head)
        if bb[2]-bb[0] <= px2-px1-28: cur = test
        else:
            if cur: lines2.append(cur)
            cur = w
    if cur: lines2.append(cur)
    lh = 54; hy = py1 + 80
    for line in lines2:
        d.text((px1+14, hy), line, font=f_head, fill=INK)
        hy += lh

    # Subhead
    d.line([px1+10, hy+6, px2-10, hy+6], fill=(150,140,120), width=1)
    d.text((px1+14, hy+12), subhead, font=f_sub, fill=(60,50,40))

    # Body text (fake columns — gray lines)
    col_y = hy + 45
    col_h = py2 - col_y - 20
    for col_x in [px1+14, px1+(px2-px1)//2+10]:
        for row in range(0, col_h, 18):
            lw2 = int(np.random.default_rng(col_x+row).integers(100, (px2-px1)//2-30))
            d.line([col_x, col_y+row, col_x+lw2, col_y+row], fill=(160,150,130), width=1)

    static_arr = np.array(img)

    def frame(t):
        base = static_arr.copy().astype(np.float32)
        # Subtle paper grain
        paper_grain = np.random.default_rng(int(t*12)%500).normal(0,4,(H,W,3)).astype(np.float32)
        base = np.clip(base + paper_grain, 0, 255)
        # Vignette
        base[:,:,0]*=VIG; base[:,:,1]*=VIG; base[:,:,2]*=VIG
        fi = ease(min(t/0.5,1.0)); fo = ease(min((duration-t)/0.5,1.0))
        return np.clip(base*min(fi,fo), 0, 255).astype(np.uint8)

    return frame


def bloomberg_terminal(symbol, price, change_pct, extra_lines, duration):
    """Bloomberg terminal style — green on black."""
    f_sym  = _lf(FONT_SANS_BOLD, 52)
    f_prc  = _lf(FONT_SANS_BOLD, 88)
    f_chg  = _lf(FONT_SANS_BOLD, 46)
    f_lbl  = _lf(FONT_SANS,      16)
    f_ext  = _lf(FONT_SANS,      18)

    BLM_BG  = (  8,  10,  8)
    BLM_GRN = ( 50, 220, 80)
    BLM_RED = (220,  50, 50)
    BLM_DIM = ( 80, 100, 80)
    BLM_BDR = ( 30,  45, 30)

    chg_col = BLM_GRN if not change_pct.startswith("-") else BLM_RED
    sign    = "▲" if not change_pct.startswith("-") else "▼"

    def frame(t):
        arr = np.full((H,W,3), BLM_BG, dtype=np.float32)
        # Grid lines
        for gy in range(0, H, 40):
            arr[gy:gy+1] = np.array(BLM_BDR, dtype=np.float32)
        for gx in range(0, W, 80):
            arr[:, gx:gx+1] = np.array(BLM_BDR, dtype=np.float32)

        # Top bar
        arr[0:40] = np.array([15,22,15], dtype=np.float32)

        img = Image.fromarray(arr.astype(np.uint8))
        d   = ImageDraw.Draw(img)

        # Header
        d.text((18, 8), "BLOOMBERG TERMINAL", font=f_lbl, fill=BLM_DIM)
        ts_txt = "LIVE  " + ("▐"*int((t*4)%5))
        d.text((W-140, 8), ts_txt, font=f_lbl, fill=BLM_GRN)

        p1 = ease(min(t/0.4, 1.0))
        p2 = ease(min(max((t-0.5)/0.4,0),1.0))
        p3 = ease(min(max((t-0.9)/0.4,0),1.0))

        # Symbol
        if p1>0.01:
            d.text((60+2, 68+2), symbol, font=f_sym, fill=(0,0,0,180))
            d.text((60, 68), symbol, font=f_sym, fill=(*BLM_GRN, int(255*p1)))

        # Price
        if p2>0.01:
            pb = d.textbbox((0,0), price, font=f_prc)
            px = (W-(pb[2]-pb[0]))//2
            d.text((px+3, 140+3), price, font=f_prc, fill=(0,0,0,180))
            d.text((px, 140), price, font=f_prc, fill=(*chg_col, int(255*p2)))

        # Change
        if p3>0.01:
            chg_txt = f"{sign} {change_pct}"
            cb2 = d.textbbox((0,0), chg_txt, font=f_chg)
            cx2 = (W-(cb2[2]-cb2[0]))//2
            d.text((cx2, 250), chg_txt, font=f_chg, fill=(*chg_col, int(255*p3)))

        # Extra lines
        for i, (lbl2, val2, col2) in enumerate(extra_lines):
            ep = ease(min(max((t-1.2-i*0.3)/0.4,0),1.0))
            if ep<0.01: continue
            ey = 330+i*38
            d.text((60, ey), lbl2, font=f_ext, fill=BLM_DIM)
            vb2 = d.textbbox((0,0), val2, font=f_ext)
            d.text((W-60-(vb2[2]-vb2[0]), ey), val2, font=f_ext, fill=(*col2[:3], int(255*ep)))

        # Scanline flicker
        fl = 1.0+0.03*math.sin(t*60*math.pi)
        result = np.array(img).astype(np.float32)*fl
        result = np.clip(result+GRAIN*3.5, 0, 255)
        fi = ease(min(t/0.4,1.0)); fo = ease(min((duration-t)/0.4,1.0))
        return np.clip(result*min(fi,fo), 0, 255).astype(np.uint8)

    return frame


def breaking_news(headline, ticker, color, duration):
    """CNN/BBC breaking news lower-third style."""
    f_brk  = _lf(FONT_SANS_BOLD, 18)
    f_head = _lf(FONT_SANS_BOLD, 34)
    f_tick = _lf(FONT_SANS,      16)
    f_chan = _lf(FONT_SANS_BOLD, 14)

    # Pre-render background scene (dark news studio abstract)
    def frame(t):
        arr = np.full((H,W,3), (8,8,14), dtype=np.float32)
        # Animated light sweep
        sweep = (t*0.15)%1.0; cx2 = int(sweep*W*1.4-W*0.2)
        dist2 = np.sqrt(((_x-cx2)/(W*0.45))**2+((_y-H//2)/(H*0.6))**2)
        glow = np.clip(1.0-dist2*1.2, 0, 1)*0.12
        arr[:,:,0]+=glow*color[0]; arr[:,:,1]+=glow*color[1]; arr[:,:,2]+=glow*color[2]

        img = Image.fromarray(np.clip(arr,0,255).astype(np.uint8))
        d   = ImageDraw.Draw(img)

        # Lower-third band (appears after 0.3s)
        band_p = ease(min(max((t-0.3)/0.4,0),1.0))
        if band_p > 0.01:
            band_y = int(H*0.72)
            # Slide in from left
            band_w = int(W * band_p)

            # Main band
            d.rectangle([0, band_y, band_w, band_y+58], fill=(*color[:3],))
            # Dark strip below
            d.rectangle([0, band_y+58, band_w, band_y+90], fill=(15,15,20))
            # BREAKING badge
            brk_p = ease(min(max((t-0.5)/0.3,0),1.0))
            if brk_p > 0.01:
                d.rectangle([0, band_y, 160, band_y+58], fill=(200,30,30))
                brkb = d.textbbox((0,0),"BREAKING",font=f_brk)
                d.text(((160-(brkb[2]-brkb[0]))//2, band_y+12),
                       "BREAKING", font=f_brk, fill=(255,255,255))
                d.text(((160-(brkb[2]-brkb[0]))//2, band_y+32),
                       "NEWS", font=f_brk, fill=(255,255,255))

                # Headline
                hp = ease(min(max((t-0.7)/0.4,0),1.0))
                if hp > 0.01:
                    d.text((172, band_y+12), headline, font=f_head, fill=(255,255,255))

                # Scrolling ticker
                scroll_x = int(W - (t-0.3)*220 % (W+800))
                tick_p = ease(min(max((t-1.0)/0.4,0),1.0))
                if tick_p > 0.01:
                    d.text((scroll_x, band_y+62), ticker*4, font=f_tick, fill=(200,200,200))

        result = np.array(img).astype(np.float32)
        result = np.clip(result+GRAIN*4.5,0,255)
        result[:,:,0]*=VIG; result[:,:,1]*=VIG; result[:,:,2]*=VIG
        fi = ease(min(t/0.4,1.0)); fo = ease(min((duration-t)/0.4,1.0))
        return np.clip(result*min(fi,fo), 0, 255).astype(np.uint8)

    return frame


# ════════ BUILD TIMELINE ════════════════════════════════════════
tl = Timeline(W=W, H=H)

# ── HOOK ────────────────────────────────────────────────────────
tl.add_clip(slam_text([
    ("ДВА ЧОЛОВІКИ.",      TXT, 68, 0.2),
    ("ДВА ПІДХОДИ.",       TXT, 68, 1.3),
    ("ДВА МІЛЬЯРДИ.",      YLW, 84, 2.4),
    ("І вони не згодні один з одним.", DIM, 30, 3.8),
], duration=9.0, glitch_at=2.4),
duration=9.0, transition="fade_black", transition_dur=0.5)

# ── SPLIT VS ────────────────────────────────────────────────────
tl.add_clip(split_vs(duration=12.0),
            duration=12.0, transition="dissolve", transition_dur=0.6)

# ── CTA #1 (коротка) ────────────────────────────────────────────
tl.add_clip(cta_scene(duration=14.0, is_final=False),
            duration=14.0, transition="fade_black", transition_dur=0.5)

# ── ACT 2 ───────────────────────────────────────────────────────
tl.add_clip(act_header(2,"ДВІ РЕЛІГІЇ",CB,duration=6.0),
            duration=6.0, transition="dissolve", transition_dur=0.5)

# ── BUFFETT PROFILE ─────────────────────────────────────────────
tl.add_clip(
    profile_scene(PHOTO_B,"WARREN BUFFETT","Berkshire Hathaway",
                  CB,B_CAPS,42.0,1.0,1.08,(0.5,0.5),(0.53,0.52)),
    duration=42.0, transition="burn", transition_dur=0.8)

# ── BLOOMBERG INSERT — Berkshire ────────────────────────────────
tl.add_clip(bloomberg_terminal(
    "BRK.A", "$540,000", "+19.8%/рік",
    [("Assets Under Management", "$900B",  (200,180,80)),
     ("Employees",               "360,000",(150,150,150)),
     ("Founded",                 "1965 · Omaha, NE",(100,130,100))],
    duration=9.0),
duration=9.0, transition="flash", transition_dur=0.3)

# ── BUFFETT PHILOSOPHY ──────────────────────────────────────────
tl.add_clip(slam_text([
    ("«Купуй великий бізнес.",  CB, 46, 0.3),
    ("Тримай вічно.»",          CB, 46, 1.5),
    ("Він не купує ринок.",     TXT,32, 3.0),
    ("Він купує переконання.",  TXT,32, 4.3),
], duration=13.0, accent=CB),
duration=13.0, transition="dissolve", transition_dur=0.6)

# ── DALIO PROFILE ───────────────────────────────────────────────
tl.add_clip(act_header(2,"ДРУГИЙ ГОЛОС",CD,duration=5.0),
            duration=5.0, transition="flash", transition_dur=0.3)

tl.add_clip(
    profile_scene(PHOTO_D,"RAY DALIO","Bridgewater Associates",
                  CD,D_CAPS,42.0,1.0,1.06,(0.5,0.48),(0.5,0.52)),
    duration=42.0, transition="dissolve", transition_dur=0.8)

# ── BLOOMBERG INSERT — Bridgewater ──────────────────────────────
tl.add_clip(bloomberg_terminal(
    "BRIDGEWATER", "$150B AUM", "+14% (2008)",
    [("Strategy",     "All Weather Portfolio",(50,200,180)),
     ("Clients",      "Sovereign Funds, Pensions",(150,150,150)),
     ("Founded",      "1975 · New York, NY",(100,130,100))],
    duration=9.0),
duration=9.0, transition="flash", transition_dur=0.3)

# ── DALIO PHILOSOPHY ────────────────────────────────────────────
tl.add_clip(slam_text([
    ("«Ніхто не вгадає майбутнє.",CD, 42, 0.3),
    ("Навіть найкращий.»",        CD, 42, 1.6),
    ("Він будує систему,",        TXT,30, 3.0),
    ("яка виживе при будь-якому сценарії.", TXT,30, 4.2),
], duration=13.0, accent=CD),
duration=13.0, transition="dissolve", transition_dur=0.6)

# ── COMPARISON TABLE ────────────────────────────────────────────
tl.add_clip(slam_text([
    ("Це не просто різні стратегії.", TXT, 44, 0.3),
    ("Це різні релігії.",              YLW, 58, 1.4),
], duration=7.0),
duration=7.0, transition="dissolve", transition_dur=0.5)

tl.add_clip(comparison_table(duration=55.0),
            duration=55.0, transition="dissolve", transition_dur=0.7)

# ── ACT 3 ───────────────────────────────────────────────────────
tl.add_clip(act_header(3,"МОМЕНТ ІСТИНИ — 2008",RED,duration=6.0),
            duration=6.0, transition="flash", transition_dur=0.35)

# ── NEWSPAPER INSERT ────────────────────────────────────────────
tl.add_clip(newspaper_insert(
    "\"Buy American. I Am.\"",
    "Buffett calls the bottom while the world panics",
    "THE NEW YORK TIMES, October 17, 2008",
    "THE NEW YORK TIMES",
    duration=9.0),
duration=9.0, transition="dissolve", transition_dur=0.6)

# ── 2008 CRISIS ─────────────────────────────────────────────────
tl.add_clip(
    profile_scene(PHOTO_B,"2008 — КРИЗА","Хто пройшов перевірку?",
                  RED,CRISIS_CAPS,42.0,1.0,1.05,(0.5,0.5),(0.5,0.5),do_vhs=True),
    duration=42.0, transition="dissolve", transition_dur=0.7)

# ── BREAKING NEWS ───────────────────────────────────────────────
tl.add_clip(breaking_news(
    "S&P 500 CRASHES -37% IN 2008",
    "  DOW JONES -33.8%  ·  NASDAQ -40.5%  ·  LEHMAN BROTHERS BANKRUPT  ·  ",
    RED, duration=8.0),
duration=8.0, transition="cut", transition_dur=0.0)

tl.add_clip(impact_split(
    "2008 — РЕЗУЛЬТАТИ",
    "+14%","BRIDGEWATER / Даліо",GRN,
    "−25%","BERKSHIRE / Баффет",RED,
    duration=12.0),
duration=12.0, transition="cut", transition_dur=0.0)

# ── "NOT BUFFETT" ────────────────────────────────────────────────
tl.add_clip(slam_text([
    ("Стратегія Баффета працює,",   TXT, 42, 0.3),
    ("ТІЛЬКИ якщо ти Баффет.",      RED, 56, 1.4),
    ("99% людей, що копіюють його,", TXT,30, 3.0),
    ("просто грають в азартну гру.", TXT,30, 4.2),
], duration=13.0, glitch_at=1.4),
duration=13.0, transition="dissolve", transition_dur=0.6)

# ── ACT 4 ───────────────────────────────────────────────────────
tl.add_clip(act_header(4,"ХТО ТИ НАСПРАВДІ?",YLW,duration=6.0),
            duration=6.0, transition="dissolve", transition_dur=0.5)

tl.add_clip(personality_test(duration=70.0),
            duration=70.0, transition="dissolve", transition_dur=0.7)

# ── PLOT TWIST ──────────────────────────────────────────────────
tl.add_clip(plot_twist(duration=85.0),
            duration=85.0, transition="flash", transition_dur=0.3)

# ── ACT 5 ───────────────────────────────────────────────────────
tl.add_clip(act_header(5,"ФІНАЛЬНИЙ ВИРОК",GRN,duration=6.0),
            duration=6.0, transition="dissolve", transition_dur=0.5)

tl.add_clip(verdict_scene(duration=55.0),
            duration=55.0, transition="dissolve", transition_dur=0.7)

# ── FINAL CTA (коротка) ─────────────────────────────────────────
tl.add_clip(cta_scene(duration=18.0, is_final=True),
            duration=18.0, transition="fade_black", transition_dur=0.6)

# ── OUTRO ───────────────────────────────────────────────────────
tl.add_title(
    title="БАФФЕТ vs ДАЛІО",
    subtitle="Який тип інвестора ти?  ↓ Коментуй",
    duration=10.0, transition="fade_black", transition_dur=0.8,
    bg_color=(4,4,8), title_color=(220,200,160), sub_color=(140,130,110),
)


# ════════ RENDER + AUDIO ════════════════════════════════════════
frame_fn, total = tl.build()
print(f"Duration: {total:.1f}s  ({total/60:.1f} min)")
print(f"Frames: {int(total*FPS):,}")

# ── RENDER VIDEO (no audio) ──────────────────────────────────────
render(frame_fn, total, _TMP, fps=FPS, crf=20)

# ── BUILD AUDIO TRACK ───────────────────────────────────────────
# Map scene start times (cumulative)
# Hook 0s, SplitVS 9.5s, CTA 22s, Act2 52.5s, BuffettProfile 59s,
# BuffettPhil 101.5s, Act2b 115s, DalioProfile 120.5s, DalioPhil 163s,
# Bridge 176.5s, Table 184s, Act3 239.5s, Crisis 246s, Split2008 288.5s,
# NotBuffett 301s, Act4 314.5s, PersonTest 321s, PlotTwist 391.5s,
# Act5 477s, Verdict 483.5s, FinalCTA 539s, Outro 579.5s

events = [
    # Hook slams
    (0.2,  _thud(0.4,50,9),   1.0),
    (1.3,  _thud(0.4,48,9),   0.9),
    (2.4,  _thud(0.5,38,7),   1.0),
    (2.42, _glitch_snd(0.1),  0.7),
    (3.8,  _whoosh(0.4),      0.5),
    # Split VS
    (9.5,  _chord(0.7),       0.85),
    (10.3, _drone(11.5,42),   0.35),
    # CTA
    (22.0, _thud(0.4,55,10),  0.9),
    (22.0, _drone(29.5,38),   0.28),
    # Act 2
    (52.5, _whoosh(0.5),      0.7),
    (52.7, _thud(0.5,44,8),   0.9),
    # Buffett profile
    (59.5, _drone(41.0,40),   0.32),
    # Act 2b (Dalio)
    (115.0,_chord(0.7),       0.8),
    (115.0,_drone(5.0,35),    0.3),
    # Dalio profile
    (121.0,_drone(41.0,36),   0.30),
    # Bridge
    (176.5,_thud(0.4,52,9),   0.85),
    # Table
    (184.5,_drone(54.0,44),   0.28),
    # Act 3
    (239.5,_chord(0.8),       1.0),
    (240.0,_riser(5.5,28,75), 0.6),
    # Crisis
    (246.5,_drone(41.0,34),   0.5),
    (246.5,_riser(15.0,32,68),0.4),
    # 2008 split
    (288.5,_thud(0.6,36,6),   1.0),
    (289.0,_chord(0.8),       0.9),
    # Not Buffett
    (301.5,_glitch_snd(0.12), 0.8),
    (301.6,_thud(0.5,48,9),   0.9),
    # Act 4
    (315.0,_whoosh(0.5),      0.65),
    (315.2,_chord(0.7),       0.75),
    # Personality test
    (321.5,_drone(69.0,40),   0.30),
    # Plot twist
    (391.5,_drone(10.0,38),   0.35),
    (402.0,_glitch_snd(0.14), 0.9),  # "ЗАЧЕКАЙ"
    (402.1,_thud(0.5,38,6),   1.0),
    (403.0,_glitch_snd(0.1),  0.6),
    (395.5,_riser(10.0,30,80),0.5),
    # Act 5
    (477.5,_chord(0.9),       1.0),
    (477.5,_drone(5.5,44),    0.4),
    # Verdict
    (484.0,_drone(54.0,38),   0.38),
    # Final CTA
    (539.5,_whoosh(0.5),      0.6),
    (540.0,_chord(0.7),       0.8),
    (540.0,_drone(39.0,45),   0.30),
    # Outro
    (580.0,_thud(0.6,50,8),   0.9),
]

print("Building audio...")
audio = build_audio(total, events)
save_wav(audio, _WAV)
print(f"Audio saved: {_WAV}")

# ── MUX VIDEO + AUDIO ───────────────────────────────────────────
mux(_TMP, _WAV, OUTPUT)

# cleanup
for f in [_TMP, _WAV]:
    try: _os.remove(f)
    except: pass

print(f"\n✓ Done: {OUTPUT}")
