package com.zzledger.app;

import android.app.Activity;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.util.AtomicFile;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.LinearLayout;
import org.json.JSONObject;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

/** Offline-only shell. The only rendered origin is bundled application content. */
public final class MainActivity extends Activity {
    private static final String HOST = "appassets.androidplatform.net";
    private static final int IMPORT = 101, EXPORT = 102, LIMIT = 10 * 1024 * 1024;
    private WebView web;
    private final ExecutorService io = Executors.newSingleThreadExecutor();
    private ValueCallback<Uri[]> fileCallback;
    private String exportId, exportContent;
    private AtomicFile ledger;
    private volatile boolean writing;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        ledger = new AtomicFile(new File(getFilesDir(), "ledger.json"));
        LinearLayout root = new LinearLayout(this);
        root.setFitsSystemWindows(true);
        root.setBackgroundColor(0xFFFAF8F5);
        WebView.setWebContentsDebuggingEnabled((getApplicationInfo().flags & android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE) != 0);
        web = new WebView(this);
        web.setBackgroundColor(0xFFFAF8F5);
        root.addView(web,new LinearLayout.LayoutParams(-1,-1));
        setContentView(root);
        WebSettings settings=web.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(false);
        settings.setAllowFileAccess(false);
        // ACTION_OPEN_DOCUMENT grants access to the selected content URI.
        settings.setAllowContentAccess(true);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setSupportMultipleWindows(false);
        web.addJavascriptInterface(new Bridge(),"ZZNative");
        web.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view,WebResourceRequest request) { return true; }
            @Override public WebResourceResponse shouldInterceptRequest(WebView view,WebResourceRequest request) {
                Uri u=request.getUrl();
                if (!"https".equals(u.getScheme()) || !HOST.equals(u.getHost())) return denied();
                String path=u.getPath();
                if (path==null || !path.startsWith("/assets/") || path.contains("..")) return denied();
                String name=path.substring(8);
                String mime=name.endsWith(".html")?"text/html":name.endsWith(".js")?"application/javascript":name.endsWith(".css")?"text/css":name.endsWith(".png")?"image/png":"application/octet-stream";
                try { return new WebResourceResponse(mime,"UTF-8",getAssets().open(name)); }
                catch(IOException error) { return denied(); }
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override public boolean onShowFileChooser(WebView view,ValueCallback<Uri[]> callback,FileChooserParams params) {
                if(fileCallback!=null) fileCallback.onReceiveValue(null);
                fileCallback=callback;
                Intent intent=new Intent(Intent.ACTION_OPEN_DOCUMENT);
                intent.addCategory(Intent.CATEGORY_OPENABLE);
                intent.setType("*/*");
                intent.putExtra(Intent.EXTRA_MIME_TYPES,new String[]{"application/json","text/plain","application/octet-stream"});
                try { startActivityForResult(intent,IMPORT); }
                catch(Exception error) { fileCallback.onReceiveValue(null);fileCallback=null; }
                return true;
            }
        });
        web.loadUrl("https://"+HOST+"/assets/index.html");
    }
    private WebResourceResponse denied() {
        return new WebResourceResponse("text/plain","UTF-8",403,"Forbidden",Collections.emptyMap(),new ByteArrayInputStream(new byte[0]));
    }
    private byte[] readLimited(InputStream in) throws IOException {
        if(in==null) throw new IOException("无法读取文件");
        try(InputStream input=in;ByteArrayOutputStream output=new ByteArrayOutputStream()) {
            byte[] buffer=new byte[8192];int n;
            while((n=input.read(buffer))!=-1){ if(output.size()+n>LIMIT) throw new IOException("账本最大支持 10 MB");output.write(buffer,0,n); }
            return output.toByteArray();
        }
    }
    private void atomicWrite(AtomicFile target,byte[] content) throws IOException {
        FileOutputStream stream=null;
        try { stream=target.startWrite();stream.write(content);target.finishWrite(stream); }
        catch(IOException error){ if(stream!=null) target.failWrite(stream);throw error; }
    }
    private void reply(String id,String value,String error) {
        JSONObject result=new JSONObject();
        try { if(error!=null) result.put("error",error);else result.put("value",value==null?JSONObject.NULL:value); }
        catch(Exception ignored) { return; }
        final String js="window.zzNativeReply("+JSONObject.quote(id)+","+result+")";
        runOnUiThread(()->{if(!isDestroyed()) web.evaluateJavascript(js,null);});
    }
    private final class Bridge {
        @JavascriptInterface public void request(String id,String action,String payload) {
            io.execute(()-> {
                try {
                    JSONObject args=new JSONObject(payload);
                    if("read".equals(action)) {
                        try { reply(id,new String(readLimited(ledger.openRead()),StandardCharsets.UTF_8),null); }
                        catch(FileNotFoundException missing) { if(ledger.getBaseFile().exists()) throw missing; reply(id,null,null); }
                    } else if("write".equals(action)) {
                        String raw=args.getString("value");byte[] bytes=raw.getBytes(StandardCharsets.UTF_8);
                        if(bytes.length>LIMIT) throw new IOException("账本最大支持 10 MB");
                        JSONObject data=new JSONObject(raw);
                        if(data.getInt("version")!=1 || data.optJSONArray("accounts")==null || data.optJSONArray("entries")==null) throw new IOException("账本格式不正确");
                        writing=true;
                        try {
                            if(ledger.getBaseFile().exists()) atomicWrite(new AtomicFile(new File(getFilesDir(),"ledger.previous.json")),readLimited(ledger.openRead()));
                            atomicWrite(ledger,bytes);
                        } finally {writing=false;}
                        reply(id,null,null);
                    } else if("export".equals(action)) {
                        String content=args.getString("content"),name=args.getString("filename");
                        if(content.getBytes(StandardCharsets.UTF_8).length>LIMIT) throw new IOException("导出文件过大");
                        if(!name.matches("[^/\\\\]+\\.(json|csv)")) throw new IOException("导出文件名无效");
                        runOnUiThread(()->startExport(id,content,name));
                    } else throw new IOException("不支持的操作");
                } catch(Exception error) { reply(id,null,error.getMessage()==null?"本地文件操作失败":error.getMessage()); }
            });
        }
        @JavascriptInterface public void finishApp(){runOnUiThread(()->{if(!writing && exportId==null) finish();});}
    }
    private void startExport(String id,String content,String name) {
        if(exportId!=null) {reply(id,null,"请先完成上一次导出");return;}
        exportId=id;exportContent=content;
        Intent intent=new Intent(Intent.ACTION_CREATE_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType(name.endsWith(".csv")?"text/csv":"application/json");
        intent.putExtra(Intent.EXTRA_TITLE,name);
        try {startActivityForResult(intent,EXPORT);}
        catch(Exception error) {exportId=null;exportContent=null;reply(id,null,"无法打开系统文件选择器");}
    }
    @Override protected void onActivityResult(int request,int result,Intent data) {
        super.onActivityResult(request,result,data);
        if(request==IMPORT && fileCallback!=null) {
            ValueCallback<Uri[]> callback=fileCallback;fileCallback=null;
            if(result!=RESULT_OK || data==null || data.getData()==null){callback.onReceiveValue(null);return;}
            final Uri uri=data.getData();
            // Bound the selected document before WebView reads it through the file input.
            io.execute(()->{
                try {
                    readLimited(getContentResolver().openInputStream(uri));
                    runOnUiThread(()->callback.onReceiveValue(new Uri[]{uri}));
                } catch(Exception error){runOnUiThread(()->{callback.onReceiveValue(null);web.evaluateJavascript("alert("+JSONObject.quote("导入失败："+error.getMessage())+")",null);});}
            });
        } else if(request==EXPORT && exportId!=null) {
            final String id=exportId,content=exportContent;exportId=null;exportContent=null;
            if(result!=RESULT_OK || data==null || data.getData()==null){reply(id,null,"已取消导出");return;}
            final Uri uri=data.getData();
            io.execute(()->{
                try(OutputStream out=getContentResolver().openOutputStream(uri,"wt")) {
                    if(out==null) throw new IOException("无法写入所选文件");
                    out.write(content.getBytes(StandardCharsets.UTF_8));out.flush();reply(id,"saved",null);
                } catch(Exception error){reply(id,null,"导出失败："+error.getMessage());}
            });
        }
    }
    @Override public void onBackPressed(){web.evaluateJavascript("window.zzMobileBack && window.zzMobileBack()",null);}
    @Override protected void onDestroy(){if(fileCallback!=null) fileCallback.onReceiveValue(null);web.removeJavascriptInterface("ZZNative");web.destroy();io.shutdown();super.onDestroy();}
}
