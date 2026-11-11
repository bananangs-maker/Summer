import unittest, tempfile, os, sys
from pathlib import Path
from unittest.mock import patch, MagicMock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from storage import Store, Conflict
class StorageTests(unittest.TestCase):
    def test_production_requires_database(self):
        with patch.dict(os.environ, {'RENDER':'true','DATABASE_URL':''}):
            with self.assertRaisesRegex(RuntimeError,'requires DATABASE_URL'):Store()
    def pgstore(self):
        obj=Store.__new__(Store);obj.url='postgresql://example/unused';return obj
    def test_postgres_connect_secure_options(self):
        fake=MagicMock()
        with patch.dict(sys.modules, {'psycopg':fake}):
            self.pgstore().connect()
        kwargs=fake.connect.call_args.kwargs
        self.assertEqual(kwargs['sslmode'],'require')
        self.assertIsNone(kwargs['prepare_threshold'])
    def test_postgres_atomic_update(self):
        obj=self.pgstore();c=MagicMock();c.__enter__.return_value=c
        c.execute.return_value.fetchone.return_value=(3,)
        with patch.object(obj,'connect',return_value=c):
            self.assertEqual(obj.write(2,{'logs':[]}),3)
        sql,args=c.execute.call_args.args
        self.assertIn('AND revision=%s RETURNING revision',sql)
        self.assertEqual(args[1],2)
        c.close.assert_called_once()
    def test_postgres_conflict(self):
        obj=self.pgstore();c=MagicMock();c.__enter__.return_value=c
        c.execute.return_value.fetchone.return_value=None
        with patch.object(obj,'connect',return_value=c):
            with self.assertRaises(Conflict):obj.write(0,{})
    def test_postgres_jsonb_read(self):
        obj=self.pgstore();c=MagicMock();c.execute.return_value.fetchone.return_value=(4,{'logs':[]})
        with patch.object(obj,'connect',return_value=c):self.assertEqual(obj.read(),(4,{'logs':[]}))
        c.close.assert_called_once()
    def test_private_schema_initialization(self):
        obj=self.pgstore();c=MagicMock();c.__enter__.return_value=c
        with patch.object(obj,'connect',return_value=c):obj.initialize()
        sql=' '.join(call.args[0] for call in c.execute.call_args_list)
        self.assertIn('motion_private',sql);self.assertIn('ENABLE ROW LEVEL SECURITY',sql)
        self.assertIn('ON CONFLICT (id) DO NOTHING',sql)
if __name__=='__main__':unittest.main()
