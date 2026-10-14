import copy
import json
import tempfile
import unittest
from zzledger.domain import validate_ledger
from zzledger.storage import LedgerStore

def sample():
    return {'version':1,'accounts':[{'id':'a','name':'微信','type':'微信','balance':9000},{'id':'b','name':'银行','type':'银行卡','balance':11000}], 'entries':[], 'transfers':[{'id':'t','fromAccountId':'a','toAccountId':'b','amount':1000,'date':'2026-10-14','note':'划转'}]}

class TransferTests(unittest.TestCase):
    def test_persistence_and_old_ledger(self):
        data=sample()
        with tempfile.TemporaryDirectory() as folder:
            store=LedgerStore(folder)
            store.write(json.dumps(data))
            self.assertEqual(json.loads(LedgerStore(folder).read()),data)
            legacy=copy.deepcopy(data); legacy.pop('transfers')
            store.write(json.dumps(legacy))
            self.assertEqual(json.loads(store.backup.read_text(encoding='utf-8')),data)
            validate_ledger(legacy)
    def test_invalid_transfers(self):
        for change in [{'amount':0},{'amount':True},{'amount':1.5},{'amount':10**12},{'fromAccountId':'b'},{'toAccountId':'x'},{'date':'2026-02-30'},{'note':None},{'id':''}]:
            data=sample(); data['transfers'][0].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError): validate_ledger(data)
        for value in [None, {}, [sample()['transfers'][0]]*2]:
            data=sample(); data['transfers']=value
            with self.assertRaises(ValueError): validate_ledger(data)
    def test_invalid_save_preserves_file(self):
        with tempfile.TemporaryDirectory() as folder:
            store=LedgerStore(folder); data=sample(); store.write(json.dumps(data)); before=store.read()
            data['transfers'][0]['toAccountId']='missing'
            with self.assertRaises(ValueError): store.write(json.dumps(data))
            self.assertEqual(store.read(),before)
