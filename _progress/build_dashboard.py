#!/usr/bin/env python3
# 使い方: python3 build_dashboard.py notes.json
# Gistのnotes.jsonから 科目>タブ>項目 の達成率ダッシュボードHTMLを再生成する。
import json,re,os,glob,sys,urllib.parse as U
from collections import OrderedDict
HERE=os.path.dirname(os.path.abspath(__file__))
REPO=os.path.dirname(HERE)                       # = dashboard（独立リポ 2026-07-11分離）
MATOME=os.path.dirname(REPO)                     # = まとめ（教材のスキャン元）
BASE=os.path.join(MATOME,'1ヶ月前チェック')      # 集計対象の教材はまとめ側に残置
OUT=os.path.join(REPO,'学習進捗ダッシュボード.html')
notes_path=sys.argv[1] if len(sys.argv)>1 else os.path.join(HERE,'notes.json')
d={}  # notes.json の中身。build_data() で読み込む
def keep(p):
    if 'memo_archive' in p or '_progress' in p:return False
    if os.path.basename(p)=='学習進捗ダッシュボード.html':return False
    # 経済学は「前半/後半の2ファイル」だけ集計対象にする（統合版・各論・練習問題は除外）
    if '経済学' in p and ('前半' not in p and '後半' not in p):return False
    # 作業用の使い捨て（〇〇テスト・_編集テスト・sandbox等）は集計に混ぜない。
    # 本物の教材と同じ論点名で二重に並んでしまうため（2026-07-17 ⑤事業再編が2行出た件）。
    b=os.path.basename(p)
    if re.search(r'(テスト|_sandbox|sandbox_|_完成イメージ|コピー|copy)',b,re.I):return False
    return True
files=[p for p in glob.glob(BASE+'/**/*.html',recursive=True) if keep(p)]
def jl(k,dv):
    v=d.get(k)
    if v is None:return dv
    try:return json.loads(v) if isinstance(v,str) else v
    except:return dv
def cleanS(s):return re.sub(r'\s+',' ',re.sub('<[^>]+>','',s)).strip()
def norm(s):return re.sub(r'[\s　「」・、。（）()／/,．.:：]','',re.sub('<[^>]+>','',s))
def analyze(p):
    html=open(p,encoding='utf-8').read();fn=os.path.basename(p)
    m=re.search(r'(qz2?\d+)_pin_v1',html);pref=m.group(1) if m else None
    tabs=[cleanS(t) for t in re.findall(r'class="tab-btn[^"]*"[^>]*>(.*?)</',html)]
    body=re.sub(r'__qzseed_data.*?</script>','',html,flags=re.S)
    ev=[]
    tabmarks=[(mm.start(),int(mm.group(1))) for mm in re.finditer(r'id="tab(\d+)"',body)]
    if not tabmarks:
        # 経済の直前ノート等：パネルidが id="tabN" でなく id="qNN_tabM" 形式。
        # sw(n) は .tab-content の DOM 出現順(i番目)で切替＝並び順をタブ番号として使う（タブ名 tabs[i] に対応）。
        conts=list(re.finditer(r'class="tab-content[^"]*"',body))
        # 誤割当防止：tab-content の数がタブボタン数と一致するときだけ順番割当を採用
        if conts and len(conts)==len(tabs):
            tabmarks=[(mm.start(),i) for i,mm in enumerate(conts)]
    for pos,ti in tabmarks:ev.append((pos,'TAB',ti,''))
    for mm in re.finditer(r'<div[^>]*class="[^"]*fill-card[^"]*"[^>]*>',body):
        tag=mm.group(0);idm=re.search(r'id="([^"]+)"',tag)
        cid=idm.group(1) if idm else 'card@'+str(mm.start())
        hm=re.search(r'<div class="fill-header[^"]*">(.*?)</div>',body[mm.end():mm.end()+500],re.S)
        ev.append((mm.start(),'CARD',cid,cleanS(hm.group(1)) if hm else cid))
    for mm in re.finditer(r'class="fill-blank"',body):ev.append((mm.start(),'BLK',None,''))
    for mm in re.finditer(r'class="chk\d+-qt"[^>]*>([^<]{1,140})',body,re.S):
        ev.append((mm.start(),'Q',None,cleanS(mm.group(1))))
    # 論点チェック（○×）カード：非表示(折りたたみ)状態は qzNN_rhide_v1 に保存済み
    for mm in re.finditer(r'<div[^>]*class="[^"]*ronten-card[^"]*"[^>]*>',body):
        idm=re.search(r'id="([^"]+)"',mm.group(0))
        if idm:ev.append((mm.start(),'RONT',idm.group(1),''))
    ev.sort()
    pin=jl(pref+'_pin_v1','{}') if pref else {}
    if not isinstance(pin,dict):pin={}
    rhide=jl(pref+'_rhide_v1','{}') if pref else {}
    if not isinstance(rhide,dict):rhide={}
    curtab=curcard=None;cards=OrderedDict();ronten=[]
    for pos,t,v,txt in ev:
        if t=='TAB':curtab=v
        elif t=='CARD':curcard=v;cards[v]={'tab':curtab,'title':txt,'blk':0,'q':0,'qtexts':[]}
        elif t=='RONT':ronten.append((v,curtab))
        elif curcard is None:continue
        elif t=='BLK':cards[curcard]['blk']+=1
        elif t=='Q':cards[curcard]['q']+=1;cards[curcard]['qtexts'].append(norm(txt))
    rt_by_tab={}   # tab -> [総数, 非表示済]
    for rid,tb in ronten:
        a=rt_by_tab.setdefault(tb,[0,0]);a[0]+=1
        if rhide.get(rid):a[1]+=1
    hidden=[]
    for k in d:
        if k.startswith('sec-hide:') and fn in U.unquote(k):
            vv=jl(k,{})
            if isinstance(vv,dict):hidden+=list(vv.keys())
    donecardq={}
    for hk in hidden:
        s=re.sub(r':\d+$','',re.sub(r'^[^:]*:','',hk));hn=norm(s)[:24]
        if len(hn)<6:continue
        best=None
        for cid,c in cards.items():
            for qt in c['qtexts']:
                if qt.startswith(hn) or (hn.startswith(qt[:24]) and len(qt)>=10):best=cid;break
            if best:break
        if best:donecardq[best]=donecardq.get(best,0)+1
    out=[]
    for cid,c in cards.items():
        dq=min(donecardq.get(cid,0),c['q'])
        df=min(len(pin.get(cid,[])) if isinstance(pin.get(cid),list) else 0,c['blk'])
        out.append({'id':cid,'tab':c['tab'],'title':c['title'],'q':c['q'],'dq':dq,'blk':c['blk'],'df':df})
    return fn,pref,tabs,out,rt_by_tab
def cat(p):return p.replace(BASE+os.sep,'').split(os.sep)[0].replace('直前対策講座－','').replace('_冊子','')

# ---- 最終暗記まとめ（別枠集計・2026-07-18） ----
# 本体（1ヶ月前チェック）の達成率には混ぜない。科目タブの一番最後に独立ブロックで出す。
# 構造が本体と違う：fill-card / pin_v1 を使わず、.cat（cat-head .ttl＝論点名）配下に
# ○×論点チェック(.ronten-q) と ⚡実践チェック(.chk30-qt) が並ぶ。済＝sec-hide（非表示）。
EXTRA_DIR=os.path.join(MATOME,'_最終暗記まとめ_サンプル')
EXTRA_SUBJ=[('経営法務','経営法務'),('運営管理','運営管理'),('中小企業','中小企業経営・政策'),
            ('企業経営理論','企業経営理論'),('財務会計','財務・会計'),('経営情報システム','経営情報システム')]
_SIG=re.compile(r'[0-9A-Za-z぀-ヿ一-鿿]+')
def sig(s):return ''.join(_SIG.findall(re.sub('<[^>]+>','',s)))   # 絵文字・記号・空白を落とした照合用キー
def extra_subject(fn):
    for kw,subj in EXTRA_SUBJ:
        if kw in fn:return subj
    return None
def analyze_extra(p):
    fn=os.path.basename(p)
    html=open(p,encoding='utf-8').read()
    html=re.sub(r'<a class="srclink".*?</a>','',html,flags=re.S)   # 参照リンク📄は本文扱いしない
    hidden=[]
    for k in d:
        if k.startswith('sec-hide:') and fn in U.unquote(k):
            vv=jl(k,{})
            if isinstance(vv,dict):hidden+=list(vv.keys())
    hn=[sig(re.sub(r':\d+$','',re.sub(r'^[^:]*:','',k)))[:16] for k in hidden]
    hn=[x for x in hn if len(x)>=8]
    ev=[]
    for mm in re.finditer(r'<span class="ttl">(.*?)</span>',html):ev.append((mm.start(),'TTL',cleanS(mm.group(1))))
    for mm in re.finditer(r'<div class="ronten-q">(.{1,600}?)</div>',html,re.S):ev.append((mm.start(),'Q',sig(mm.group(1))))
    for mm in re.finditer(r'<div class="chk30-qt">(.{1,1500}?)</div>',html,re.S):ev.append((mm.start(),'Q',sig(mm.group(1))))
    for mm in re.finditer(r'class="fill-blank"',html):ev.append((mm.start(),'BLK',''))
    ev.sort()
    cats=[];cur=None
    for pos,t,v in ev:
        if t=='TTL':cur={'name':v,'qs':[],'blk':0};cats.append(cur)
        elif cur is None:continue
        elif t=='Q':cur['qs'].append(v)
        else:cur['blk']+=1
    out=[];tot=done=blk=0
    for c in cats:
        if not c['qs']:continue        # 全範囲マップ・混同くらべ（問題なし）は論点として数えない
        dn=sum(1 for q in c['qs'] if any(q.startswith(x) for x in hn))
        out.append({'name':c['name'],'q':len(c['qs']),'dq':dn,'blk':c['blk'],
                    'pct':round(dn/len(c['qs'])*100)})
        tot+=len(c['qs']);done+=dn;blk+=c['blk']
    return {'file':fn,'q':tot,'dq':done,'blk':blk,'pct':round(done/(tot or 1)*100),'cats':out}
def build_extra():
    ex=OrderedDict()
    if not os.path.isdir(EXTRA_DIR):return ex
    for fp in sorted(glob.glob(EXTRA_DIR+'/*_m.html')):
        subj=extra_subject(os.path.basename(fp))
        if not subj:continue
        ex[subj]=analyze_extra(fp)
    return ex

# ---- 頻出論点ロードマップ（ランクS〜D・コスパ◎○△✕）の取り込み ----
ROADMAP_DIR=os.path.join(os.path.dirname(BASE),'00_総合整理')
ROADMAP_FILE={
    '経営法務':'経営法務_頻出論点_学習ロードマップ_m.html',
    '経営情報システム':'経営情報システム_頻出論点_学習ロードマップ_m.html',
    '運営管理':'運営管理_計算論点_学習ロードマップ_m.html',
    '財務・会計':'財務会計_計算論点_学習ロードマップ_m.html',
    '企業経営理論':'企業経営理論_頻出論点_学習ロードマップ_m.html',
    '中小企業経営・政策':'中小企業経営政策_頻出論点_学習ロードマップ_m.html',
}
# 各科目：こちらのタブ名に含まれるキーワード -> ロードマップの論点名
ROADMAP_KW={
 '経営法務':[
    ('特許','特許法'),('意匠','意匠法'),('商標','商標法'),('侵害','知財侵害'),
    ('著作','著作権法'),('不競','不正競争防止法'),('国際条約','国際条約'),
    ('機関','機関'),('設立','設立'),('株式','株式'),('計算','計算書類'),
    ('再編','組織再編'),('契約','契約'),('保証','債権'),('担保','物権'),
    ('相続','相続'),('倒産','民事再生'),('国際取引','国際契約'),
 ],
 '経営情報システム':[
    ('インターネットプロトコル','TCP/IP'),('ネットワーク','LAN・WAN'),
    ('セキュリティ','暗号・認証'),('経営情報システムの種類','情報戦略'),
    ('近年のIT','クラウド・仮想化'),('開発プロセス','開発工程'),
    ('設計・開発・テスト','開発手法'),('プログラム言語','プログラミング言語'),
    ('Webアプリ','Web技術'),('ITトレンド','IoT・先端技術'),
    ('メモリ','記憶装置'),('入出力','入出力インタフェース'),('ソフトウェア','OS'),
    ('DB・SQL','トランザクション'),('性能・信頼性','信頼性'),
 ],
 '運営管理':[
    ('品質・設備','稼働率計算'),('店舗・陳列','棚割'),('販売促進','広告分析'),
    ('商品予算','値入率'),('物流センター','物流ABC'),('流通情報','アソシエーション'),
    ('生産形態','ロット生産'),('効率化指標','人時生産性'),('生産計画','生産計画最適化'),
    ('在庫管理','EOQ'),('IE','ワークサンプリング'),
 ],
 '財務・会計':[
    ('損益分岐','損益分岐点'),('資本コスト','WACC'),('リスクとリターン','期待収益率・リスク'),
    ('投資評価','NPV'),('経営分析','財務比率計算'),('税効果','繰延税金資産・負債'),
    ('CF計算','営業活動CF'),('総合原価','月末仕掛品原価'),('簿記','貸借対照表'),
    ('MM理論','MM理論'),('株価指標','マルチプル法'),('配当割引','配当割引モデル'),
 ],
 '企業経営理論':[
    ('VRIO','RBV・VRIO'),('ドメイン','ドメイン'),('多角化','アンゾフ・多角化'),
    ('競争戦略','ファイブフォース・差別化'),('技術戦略','技術経営・MOT'),
    ('M&A','M&A・戦略的提携'),('CSR','CSR・ステークホルダー'),
    ('組織構造','構造設計'),('モチベーション','動機づけ理論'),
    ('リーダーシップ','リーダーシップ論'),('労働契約','労働基準法・労災'),
    ('消費者行動','購買意思決定'),('ブランディング','ブランド戦略'),
    ('プライシング','価格設定'),('コミュニケーション','広告・販促'),('サービス','サービスマーケ'),
 ],
 '中小企業経営・政策':[
    ('下請','下請法・下請振興'),('基本法','基本法の理念・定義'),('税制','中小企業税制'),
    ('組合','中小企業組合'),('経営基盤','連携事業支援'),('経営安定','経営セーフティ共済'),
    ('経営革新','経営革新計画'),('新たな事業展開','連携事業支援'),
    ('小規模企業支援','小規模企業振興基本法'),('共済','小規模企業共済'),
    ('定義','中小企業の定義'),('実態','企業数・事業所数の動向'),('動向','業種別動向'),
    ('経営力','経営強化法'),('成長戦略','経営強化法'),('小規模事業者','小規模事業者の実態'),
 ],
}
RANK_ORDER={'S':0,'A':1,'B':2,'C':3,'D':4,'E':5}
def load_roadmap(subject):
    fp=ROADMAP_FILE.get(subject)
    if not fp:return {}
    full=os.path.join(ROADMAP_DIR,fp)
    if not os.path.exists(full):return {}
    h=open(full,encoding='utf-8').read()
    m=re.search(r'const D=\[(.*?)\];',h,re.S)
    if not m:return {}
    best={}
    for o in re.findall(r'\{[^{}]*\}',m.group(1)):
        rn=re.search(r'[{,]\s*["\']?r["\']?\s*:\s*["\']([SABCDE])',o)
        nn=re.search(r'[{,]\s*["\']?n["\']?\s*:\s*["\']([^"\']+)',o)
        cn=re.search(r'[{,]\s*["\']?c["\']?\s*:\s*["\']([◎○△✕×]?)',o)
        if not (rn and nn):continue
        n=nn.group(1);r=rn.group(1);c=cn.group(1) if cn else ''
        if n not in best or RANK_ORDER.get(r,9)<RANK_ORDER.get(best[n][0],9):
            best[n]=(r,c)
    return best
def roadmap_for_tab(subject,tabname,rm):
    for kw,name in ROADMAP_KW.get(subject,[]):
        if kw in tabname and name in rm:
            return rm[name]   # (rank,cospa)
    return (None,None)

def build_data(np):
  global d
  d=json.load(open(np,encoding='utf-8'))
  data=OrderedDict()
  RM_CACHE={}
  for p in sorted(files):
    fn,pref,tabs,cards,rt_by_tab=analyze(p)
    if not pref:continue
    subj=cat(p)
    if subj not in RM_CACHE:RM_CACHE[subj]=load_roadmap(subj)
    rm=RM_CACHE[subj]
    tabmap=OrderedDict((i,{'name':tn,'cards':[]}) for i,tn in enumerate(tabs))
    for c in cards:tabmap.setdefault(c['tab'],{'name':'tab%s'%c['tab'],'cards':[]})['cards'].append(c)
    tabsout=[]
    for i,tv in tabmap.items():
        # クイズ＝⚡チェック＋論点チェック(○×)。論点チェックの「非表示(折りたたみ)」＝済
        rt_tot,rt_done=rt_by_tab.get(i,[0,0])
        tq=sum(c['q'] for c in tv['cards'])+rt_tot;tdq=sum(c['dq'] for c in tv['cards'])+rt_done
        tb=sum(c['blk'] for c in tv['cards']);tdf=sum(c['df'] for c in tv['cards'])
        den=(tq+tb) or 1
        rank,cospa=roadmap_for_tab(subj,tv['name'],rm)
        tabsout.append({'name':tv['name'],'q':tq,'dq':tdq,'blk':tb,'df':tdf,'pct':round((tdq+tdf)/den*100),
                        'rank':rank,'cospa':cospa,'cards':tv['cards']})
    tQ=sum(t['q'] for t in tabsout);tDQ=sum(t['dq'] for t in tabsout)
    tB=sum(t['blk'] for t in tabsout);tDF=sum(t['df'] for t in tabsout)
    data.setdefault(cat(p),[]).append({'file':fn,'q':tQ,'dq':tDQ,'blk':tB,'df':tDF,
        'pct':round((tDQ+tDF)/((tQ+tB)or 1)*100),'tabs':tabsout})
  for c in data:data[c].sort(key=lambda f:f['pct'],reverse=True)
  def catpct(fs):
    a=sum(f['dq']+f['df'] for f in fs);b=sum(f['q']+f['blk'] for f in fs) or 1;return a/b
  return OrderedDict(sorted(data.items(),key=lambda kv:catpct(kv[1]),reverse=True))

def _idx(D):
  m={}
  for s,fs in D.items():
    for f in fs:
      for t in f['tabs']:
        m[(s,f['file'],t['name'])]={'dq':t['dq'],'df':t['df'],'q':t['q'],'blk':t['blk'],'pct':t['pct'],
                                    'cards':{c['title']:(c['dq'],c['df']) for c in t['cards']}}
  return m
def _tot(D):
  a=b=0
  for s,fs in D.items():
    for f in fs:a+=f['dq']+f['df'];b+=f['q']+f['blk']
  return a,b
def compute_diff(old,new):
  O,N=_idx(old),_idx(new)
  oa,ob=_tot(old);na,nb=_tot(new)
  subs={};tabs=[]
  for k,v in N.items():
    ov=O.get(k)
    if not ov:continue
    dd=(v['dq']+v['df'])-(ov['dq']+ov['df'])
    if dd:subs[k[0]]=subs.get(k[0],0)+dd
    ddq=v['dq']-ov['dq'];ddf=v['df']-ov['df']
    if ddq or ddf:
      cch=[]
      for title,(cdq,cdf) in v['cards'].items():
        ocd=ov['cards'].get(title,(0,0));a=cdq-ocd[0];b=cdf-ocd[1]
        if a or b:cch.append({'title':title,'dq':a,'df':b})
      tabs.append({'subj':k[0],'file':k[1],'tab':k[2],'ddq':ddq,'ddf':ddf,'op':ov['pct'],'np':v['pct'],'cards':cch})
  tabs.sort(key=lambda x:-(x['ddq']+x['ddf']))
  return {'oa':oa,'na':na,'ob':ob,'nb':nb,
          'subs':[{'name':s,'d':n} for s,n in sorted(subs.items(),key=lambda x:-x[1])],'tabs':tabs}
def print_diff(df):
  print('━━━ 更新差分 ━━━')
  if df['na']==df['oa'] and not df['tabs']:print('  変化なし')
  print('  達成 %d → %d (%+d)  %d%% → %d%%'%(df['oa'],df['na'],df['na']-df['oa'],
        round(df['oa']/(df['ob'] or 1)*100),round(df['na']/(df['nb'] or 1)*100)))
  if df['subs']:print('  科目別: '+' / '.join('%s +%d'%(s['name'],s['d']) for s in df['subs']))
  for t in df['tabs']:
    seg=[]
    if t['ddq']:seg.append('クイズ%+d'%t['ddq'])
    if t['ddf']:seg.append('穴埋め%+d'%t['ddf'])
    print('   [%s] %s：%s  %d%%→%d%%'%(t['subj'],t['tab'],'・'.join(seg),t['op'],t['np']))

LOG_PATH=os.path.join(HERE,'update_log.json')
def load_log():
  try:return json.load(open(LOG_PATH,encoding='utf-8'))
  except:return []
def save_log(log):json.dump(log,open(LOG_PATH,'w',encoding='utf-8'),ensure_ascii=False,indent=0)

if __name__=='__main__':
  data=build_data(notes_path)
  diff=None
  prev=sys.argv[2] if len(sys.argv)>2 else None
  if prev and os.path.exists(prev):
    prevdata=build_data(prev)
    diff=compute_diff(prevdata,data)
  # 更新履歴に記録（変化があるときだけ・タイムスタンプは呼び出し側UPDATE_TS）
  log=load_log()
  ts=os.environ.get('UPDATE_TS','')
  if diff and ts and (diff['na']!=diff['oa'] or diff['tabs']):
    log.append({'ts':ts,'oa':diff['oa'],'na':diff['na'],'subs':diff['subs'],'tabs':diff['tabs']})
    save_log(log)
  extra=build_extra()   # d は build_data() で最新notesを読み込み済み
  DATA=json.dumps(data,ensure_ascii=False)
  DIFF=json.dumps(diff,ensure_ascii=False) if diff else 'null'
  LOG=json.dumps(log,ensure_ascii=False)
  EXTRA=json.dumps(extra,ensure_ascii=False)
  TPL=open(os.path.join(HERE,'template.html'),encoding='utf-8').read()
  open(OUT,'w',encoding='utf-8').write(TPL.replace('__DATA__',DATA).replace('__DIFF__',DIFF)
       .replace('__LOG__',LOG).replace('__EXTRA__',EXTRA))
  tot_a=sum(f['dq']+f['df'] for fs in data.values() for f in fs)
  tot_b=sum(f['q']+f['blk'] for fs in data.values() for f in fs)
  print('OK ->',OUT)
  print('全体 %d%%  (%d/%d)  科目%d ファイル%d'%(round(tot_a/(tot_b or 1)*100),tot_a,tot_b,len(data),sum(len(v) for v in data.values())))
  if extra:
    ea=sum(v['dq'] for v in extra.values());eb=sum(v['q'] for v in extra.values())
    print('［別枠］最終暗記まとめ %d%%  (%d/%d)  科目%d'%(round(ea/(eb or 1)*100),ea,eb,len(extra)))
  if diff:print_diff(diff)
