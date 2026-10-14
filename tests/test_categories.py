import copy
import json
import tempfile
import unittest
from zzledger.domain import validate_ledger
from zzledger.storage import LedgerStore


def ledger():
    return {'version':1, 'accounts':[{'id':'wx','name':'微信','type':'微信','balance':9500}],
            'customCategories':['学习'], 'entries':[{'id':'e','accountId':'wx','kind':'expense',
              'amount':500,'date':'2026-10-14','category':'学习','note':''}]}


class CategoryTests(unittest.TestCase):
    def test_persistence_backup_and_legacy_category(self):
        with tempfile.TemporaryDirectory() as folder:
            store = LedgerStore(folder)
            data = ledger()
            store.write(json.dumps(data,ensure_ascii=False))
            self.assertEqual(json.loads(LedgerStore(folder).read()),data)
            without_entries = copy.deepcopy(data)
            without_entries['entries'] = []
            store.write(json.dumps(without_entries,ensure_ascii=False))
            self.assertEqual(json.loads(store.read())['customCategories'],['学习'])
            self.assertEqual(json.loads(store.backup.read_text(encoding='utf-8')),data)
        data.pop('customCategories')
        self.assertEqual(validate_ledger(data)['entries'][0]['category'],'学习')

    def test_invalid_names_and_lists(self):
        for category in ['', ' ', 'x'*21, '坏\n名称', None]:
            data = ledger(); data['entries'][0]['category'] = category
            with self.subTest(category=category), self.assertRaises(ValueError): validate_ledger(data)
        for categories in [None, {}, ['学习','学习'], [''], [' x '], [20]]:
            data = ledger(); data['customCategories'] = categories
            with self.subTest(categories=categories), self.assertRaises(ValueError): validate_ledger(data)


if __name__ == '__main__': unittest.main()
