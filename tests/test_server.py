import os, tempfile, unittest, sys, io, json, importlib
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
class ServerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();os.environ['DATA_DIR']=self.temp.name
        import server
        self.server=importlib.reload(server)
        self.weather_patch=patch.object(self.server,'get_weather',return_value={});self.weather_patch.start()
    def tearDown(self):self.weather_patch.stop();self.temp.cleanup()
    def call(self,method='GET',payload=None,path='/api/state',origin=None):
        body=json.dumps(payload).encode() if payload else b''
        env={'PATH_INFO':path,'REQUEST_METHOD':method,'CONTENT_LENGTH':str(len(body)),'wsgi.input':io.BytesIO(body),'HTTP_HOST':'localhost'}
        if origin:env['HTTP_ORIGIN']=origin
        status=[]
        result=b''.join(self.server.application(env,lambda s,h:status.append(s)))
        return status[0],json.loads(result)
    def test_save_conflict_restart(self):
        from engine import today
        s={'profile':{'weight':65,'target':55,'start':today().isoformat()},'logs':[],'routines':{}}
        status,p=self.call('PUT',{'revision':0,'state':s});self.assertEqual(status,'200 OK')
        self.assertEqual(self.call('PUT',{'revision':0,'state':s})[0],'409 Conflict')
        self.server=importlib.reload(self.server)
        self.server.get_weather=lambda *a,**k:{}
        self.assertEqual(self.call()[1]['state'],s)
    def test_cross_origin_rejected(self):
        self.assertEqual(self.call('PUT',{},origin='https://other.site')[0],'403 Forbidden')
    def test_bad_request_no_overwrite(self):
        self.assertEqual(self.call('PUT',{'revision':0,'state':{}})[0],'400 Bad Request')
        self.assertIsNone(self.call()[1]['state']['profile'])
if __name__=='__main__':unittest.main()
