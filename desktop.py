"""zz记启动入口；实现位于 zzledger 包。"""
from zzledger.application import main
from zzledger.storage import LedgerStore
from zzledger.server import make_server

if __name__ == "__main__":
    main()
