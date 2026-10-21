'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('ios/web/native-api.js', 'utf8');
const make = handler => {
  const window = handler ? {webkit: {messageHandlers: {zzLedger: {postMessage: handler}}}} : {};
  vm.runInNewContext(source, {window});
  return window;
};
(async () => {
  const calls = [];
  const window = make(async body => { calls.push(body); return body.action === 'import' ? null : 'saved'; });
  assert.equal(window.desktopConfig.platform, 'ios');
  assert.equal(await window.DesktopAPI.read(), 'saved');
  await window.DesktopAPI.write('{"version":1}');
  assert.equal(await window.DesktopAPI.import(), null, 'cancel must not become an empty imported ledger');
  await window.DesktopAPI.export('a,b', '账本.csv');
  assert.deepEqual(JSON.parse(JSON.stringify(calls)), [
    {action: 'read'}, {action: 'write', value: '{"version":1}'},
    {action: 'import'}, {action: 'export', content: 'a,b', filename: '账本.csv'}
  ]);
  await assert.rejects(make().DesktopAPI.read(), /iPhone/);
  await assert.rejects(make(async () => { throw new Error('磁盘写入失败'); }).DesktopAPI.write('x'), /磁盘写入失败/);
  await assert.rejects(make(async () => { throw '已取消导出'; }).DesktopAPI.export('x', 'a.json'), /已取消导出/);
  let finish;
  const delayed = make(() => new Promise(resolve => { finish = resolve; }));
  let settled = false;
  const save = delayed.DesktopAPI.write('x').then(() => { settled = true; });
  await Promise.resolve();
  assert.equal(settled, false, 'save must wait for native disk acknowledgment');
  finish(null); await save;
  assert.equal(settled, true);
  console.log('iOS bridge: PASS (payloads, cancellation, errors, disk acknowledgment)');
})().catch(error => { console.error(error); process.exitCode = 1; });
