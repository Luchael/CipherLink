#!/usr/bin/env python3
from pathlib import Path
import subprocess, concurrent.futures, sys, os, shutil
root=Path(__file__).resolve().parents[1]
src=root/'android/app/src/main/java/com/gametodo/nativeapp'
out=root/'android/build/kotlin-regression';out.mkdir(parents=True,exist_ok=True)
kotlinc=os.environ.get('KOTLINC') or shutil.which('kotlinc')
java=shutil.which('java')
cache=Path(os.environ.get('GRADLE_USER_HOME', str(Path.home()/'.gradle')))/'caches/modules-2/files-2.1'
def dependency(group,artifact,version):
    matches=list((cache/group/artifact/version).glob('*/*.jar'))
    if not matches: raise SystemExit(f'Missing dependency {group}:{artifact}:{version}; build Android first')
    return matches[0]
stdlib=Path(os.environ['KOTLIN_STDLIB']) if 'KOTLIN_STDLIB' in os.environ else dependency('org.jetbrains.kotlin','kotlin-stdlib','2.0.21')
if not kotlinc or not java: raise SystemExit('Install JDK 17 and Kotlin 2.0.21, or set KOTLINC')
android_jar=Path(os.environ.get('ANDROID_HOME', os.environ.get('ANDROID_SDK_ROOT','')))/'platforms/android-35/android.jar'
policy=['SharedPeriods.kt','RecurrenceWindow.kt','OverlayTaskPolicy.kt','OverlayEventPolicy.kt']
plans=[('BubbleGeometryTest',['BubbleGeometry.kt'],[]),('OverlayEventPolicyTest',['OverlayEventPolicy.kt'],[]),('OverlayTaskPolicyTest',policy,[]),('RecurrenceWindowTest',policy,[]),('RecurrenceAutoSafetyTest',['RecurrenceWindow.kt'],[]),('RealTimeMemoTest',['RealTimeMemo.kt'],['tests/support/JSONObject.kt']),('WeeklyProgressTest',['WeeklyProgress.kt','AutoCheckIntervals.kt'],['tests/support/JSONObject.kt'])]
for t in sorted((root/'tests/endgame').glob('Endgame*Test.kt')):plans.append((t.stem,['EndgameRecords.kt','EndgameGoals.kt','SharedPeriods.kt','RecurrenceWindow.kt'],['tests/endgame/Models.kt','tests/endgame/Stubs.kt']))
plans += [('OverlayTaskTreeTest', policy + ['TodoTask.kt','OverlayTaskTree.kt'], []),
          ('TaskSupportTest',['TaskSupport.kt','SafeFailure.kt'], []),
          ('BannerSourcePolicyTest',['StellaBanners.kt','BannerLabels.kt','BannerSource.kt','GameRules.kt','LabelGames.kt','SharedPeriods.kt','RecurrenceWindow.kt','BannerLedger.kt','BannerExpiry.kt','TodoTask.kt'],['tests/banner/TodoistStub.kt'])]
plans += [('FixedIntervalsTest',policy+['FixedIntervals.kt'],[]),('EndfieldLongTermTest',['EndfieldLongTerm.kt'],['tests/endgame/Models.kt','tests/endgame/Stubs.kt'])]
plans += [('EndfieldNotesTest',['EndfieldNotes.kt','SharedPeriods.kt','RecurrenceWindow.kt'],['tests/endgame/Stubs.kt'])]
plans += [('FloatingTaskRequestTest',['SharedPeriods.kt','RecurrenceWindow.kt','FloatingTaskDraft.kt','FloatingTaskRequest.kt'],[])]
plans += [('ResetTimePolicyTest',policy+['FloatingTaskDraft.kt'],[])]
plans += [('BannerLabelsTest',['BannerLabels.kt'],[])]
plans += [('UiJobRunnerTest',['UiJobRunner.kt'],[]),
          ('LabelGamesTest',policy+['LabelGames.kt','GameRules.kt','TodoTask.kt','OverlayTaskTree.kt'],[]),
          ('ProgressMemoTest',['ProgressMemo.kt','RealTimeMemo.kt'],['tests/support/JSONObject.kt']),
          ('ProgressPresentationTest',['ProgressPresentation.kt'],[]),
          ('TodoistOAuthPolicyTest',['TodoistOAuthPolicy.kt'],[]),
          ('DisplayOptionsTest',['DisplayOptions.kt'],[])]
def run(plan):
 name,sources,extras=plan;t=next((root/'tests').rglob(name+'.kt'));d=out/name;d.mkdir(exist_ok=True)
 extra_cp = []
 if name == 'FloatingTaskRequestTest': extra_cp.append(str(dependency('org.json','json','20240303')))
 if name in ('BannerSourcePolicyTest','LabelGamesTest'):
  extra_cp=[str(android_jar)]
  if name == 'BannerSourcePolicyTest': extra_cp.append(str(dependency('org.jsoup','jsoup','1.18.3')))
 command=[kotlinc,*[str(src/p) for p in sources],*[str(root/p) for p in extras],str(t),'-d',str(d)]
 command += ['-classpath',os.pathsep.join([str(stdlib)]+extra_cp)]
 result=subprocess.run(command,capture_output=True,text=True,cwd=root)
 log=result.stdout+result.stderr
 if result.returncode==0:
  main=('com.gametodo.nativeapp.' if 'package com.gametodo.nativeapp' in t.read_text(encoding='utf-8') else '')+name+'Kt'
  result=subprocess.run([java,'-cp',os.pathsep.join([str(d),str(stdlib)]+extra_cp),main],capture_output=True,text=True,cwd=root);log+=result.stdout+result.stderr
 (out/(name+'.log')).write_text(log,encoding='utf-8')
 return name,result.returncode,log.strip()
unknown=set(sys.argv[1:])-{p[0] for p in plans}
if unknown: raise SystemExit('Unknown tests: '+', '.join(sorted(unknown)))
plans=[p for p in plans if len(sys.argv)==1 or p[0] in sys.argv[1:]]
results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for name,code,log in pool.map(run,plans):
  results.append((name,code));print(('PASS' if code==0 else 'FAIL'),name,log[-1800:] if code else next((line for line in reversed(log.splitlines()) if not line.startswith('Picked up JAVA_TOOL_OPTIONS:')), 'completed'),flush=True)
print('SUMMARY',sum(c==0 for _,c in results),'passed',sum(c!=0 for _,c in results),'failed')
raise SystemExit(any(c for _,c in results))
