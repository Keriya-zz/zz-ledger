import copy
import json
import tempfile
import unittest
from zzledger.domain import validate_ledger
from zzledger.storage import LedgerStore


def sample():
    return {'version':1,'accounts':[{'id':'a','name':'微信','type':'微信','balance':80000}],
            'debts':[{'id':'d','name':'信用卡','creditor':'银行','amount':60000,'dueDate':'2026-10-20','note':''}],
            'entries':[{'id':'e','accountId':'a','kind':'expense','category':'还款','amount':20000,'date':'2026-10-12','note':'还款','debtId':'d'}]}


class DebtValidationTests(unittest.TestCase):
    def test_debt_and_payment_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            store=LedgerStore(folder)
            data=sample();store.write(json.dumps(data,ensure_ascii=False))
            self.assertEqual(json.loads(LedgerStore(folder).read()), data)

    def test_invalid_link_overpayment_and_dates(self):
        for change in ('missing', 'overpaid', 'income', 'category', 'bad_date', 'duplicate', 'null'):
            data=copy.deepcopy(sample())
            if change=='missing': data['entries'][0]['debtId']='missing'
            if change=='overpaid': data['entries'][0]['amount']=60001
            if change=='income': data['entries'][0]['kind']='income'
            if change=='category': data['entries'][0]['category']='餐饮'
            if change=='bad_date': data['debts'][0]['dueDate']='2026-02-30'
            if change=='duplicate': data['debts'].append(copy.deepcopy(data['debts'][0]))
            if change=='null': data['debts']=None
            with self.subTest(change=change), self.assertRaises(ValueError): validate_ledger(data)

    def test_old_ledger_and_optional_due_date(self):
        old={'version':1,'accounts':[],'entries':[]}
        self.assertEqual(validate_ledger(old),old)
        data=sample(); data['debts'][0]['dueDate']=''
        self.assertEqual(validate_ledger(data),data)


if __name__=='__main__': unittest.main()
