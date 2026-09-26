package com.caloriecast.app;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.graphics.Bitmap;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.ConnectivityManager;
import android.net.NetworkInfo;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.JavascriptInterface;
import android.webkit.PermissionRequest;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout;
import androidx.webkit.WebViewAssetLoader;

import java.io.InputStream;

public class MainActivity extends Activity {

    // --- State Constants ---
    private static final int STATE_LOADING = 0;
    private static final int STATE_CONTENT = 1;
    private static final int STATE_ERROR = 2;

    private static final String PREFS_NAME = "CalorieCastPrefs";
    private static final String KEY_SERVER_ADDRESS = "server_address";

    // Default reachable development LAN IP of host machine
    public static final String DEFAULT_DEV_IP = "172.19.217.120:8000";
    public static final String DEFAULT_BACKEND_URL = "http://" + DEFAULT_DEV_IP;

    // Self-contained, zero-latency local asset application URL (runs 100% offline from APK)
    public static final String LOCAL_APP_URL = "https://appassets.androidplatform.net/static/login.html";

    private static final int WATCHDOG_TIMEOUT_MS = 6000;
    private static final int FILE_CHOOSER_RESULT_CODE = 1001;

    // --- UI Components ---
    private FrameLayout mRootContainer;
    private SwipeRefreshLayout mSwipeRefreshLayout;
    private WebView mWebView;
    private LinearLayout mLoadingView;
    private TextView mLoadingStatusText;
    private ScrollView mErrorView;
    private TextView mErrorDetailText;
    private EditText mServerAddressInput;
    private TextView mDiagnosticsText;

    private WebViewAssetLoader mAssetLoader;
    private ValueCallback<Uri[]> mFilePathCallback;
    private final Handler mMainHandler = new Handler(Looper.getMainLooper());
    private Runnable mWatchdogRunnable;
    private boolean mPageLoadedSuccessfully = false;
    private boolean mHasPageError = false;
    private String mCurrentTargetUrl = LOCAL_APP_URL;

    // --- JavaScript Bridge ---
    public class WebAppInterface {
        @JavascriptInterface
        public void setServerAddress(final String newAddress) {
            mMainHandler.post(() -> {
                saveServerAddress(newAddress);
                Toast.makeText(MainActivity.this, "Backend server set to: " + newAddress, Toast.LENGTH_SHORT).show();
            });
        }

        @JavascriptInterface
        public String getServerAddress() {
            return getSavedServerAddress();
        }

        @JavascriptInterface
        public void showToast(final String message) {
            mMainHandler.post(() -> Toast.makeText(MainActivity.this, message, Toast.LENGTH_SHORT).show());
        }

        @JavascriptInterface
        public void reloadApp() {
            mMainHandler.post(() -> navigateToUrl(LOCAL_APP_URL));
        }
    }

    @Override
    @SuppressLint("SetJavaScriptEnabled")
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Immersive dark status bar
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            getWindow().setStatusBarColor(0xFF0F172A);
            getWindow().setNavigationBarColor(0xFF0F172A);
        }

        // Initialize WebViewAssetLoader for self-contained, lightning-fast local asset loading
        setupAssetLoader();

        // Build Native Multi-State UI Hierarchy
        buildViews();
        setContentView(mRootContainer);

        // Always launch the self-contained local app immediately (0 latency, 0 black screen risk)
        mCurrentTargetUrl = LOCAL_APP_URL;
        navigateToUrl(mCurrentTargetUrl);
    }

    /**
     * Initializes Google AndroidX WebViewAssetLoader.
     * Intercepts https://appassets.androidplatform.net/static/* and serves files directly
     * from the APK assets/static folder without network overhead.
     */
    private void setupAssetLoader() {
        mAssetLoader = new WebViewAssetLoader.Builder()
                .setHttpAllowed(true)
                .setDomain("appassets.androidplatform.net")
                .addPathHandler("/static/", new WebViewAssetLoader.PathHandler() {
                    @Override
                    public WebResourceResponse handle(String path) {
                        try {
                            String cleanPath = path.startsWith("/") ? path.substring(1) : path;
                            InputStream is = null;
                            try {
                                is = getAssets().open("static/" + cleanPath);
                            } catch (Exception e1) {
                                try {
                                    is = getAssets().open(cleanPath);
                                } catch (Exception e2) {
                                    return null;
                                }
                            }
                            String mimeType = guessMimeType(cleanPath);
                            return new WebResourceResponse(mimeType, "UTF-8", is);
                        } catch (Exception e) {
                            return null;
                        }
                    }
                })
                .build();
    }

    private String guessMimeType(String path) {
        String lower = path.toLowerCase();
        if (lower.endsWith(".html") || lower.endsWith(".htm")) return "text/html";
        if (lower.endsWith(".css")) return "text/css";
        if (lower.endsWith(".js")) return "application/javascript";
        if (lower.endsWith(".json")) return "application/json";
        if (lower.endsWith(".png")) return "image/png";
        if (lower.endsWith(".jpg") || lower.endsWith(".jpeg")) return "image/jpeg";
        if (lower.endsWith(".svg")) return "image/svg+xml";
        if (lower.endsWith(".ico")) return "image/x-icon";
        if (lower.endsWith(".webp")) return "image/webp";
        if (lower.endsWith(".woff2")) return "font/woff2";
        if (lower.endsWith(".woff")) return "font/woff";
        if (lower.endsWith(".ttf")) return "font/ttf";
        return "text/plain";
    }

    /**
     * Programmatically constructs the Native Multi-State View Hierarchy:
     * 1. Content View (SwipeRefreshLayout + WebView)
     * 2. Loading / Splash View (App branding, circular spinner, status message)
     * 3. Connection Error & Diagnostics View (Failure reason, custom IP entry, presets, retry button)
     */
    private void buildViews() {
        mRootContainer = new FrameLayout(this);
        mRootContainer.setLayoutParams(new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        mRootContainer.setBackgroundColor(0xFF0F172A); // AMOLED Dark background

        // --- 1. Content View (SwipeRefreshLayout + WebView) ---
        mSwipeRefreshLayout = new SwipeRefreshLayout(this);
        mSwipeRefreshLayout.setLayoutParams(new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        mSwipeRefreshLayout.setColorSchemeColors(0xFF38BDF8, 0xFFEF4444);
        mSwipeRefreshLayout.setProgressBackgroundColorSchemeColor(0xFF1E293B);

        mWebView = new WebView(this);
        mWebView.setLayoutParams(new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        mWebView.setBackgroundColor(0xFF0F172A);
        mWebView.setLayerType(View.LAYER_TYPE_HARDWARE, null);
        mWebView.setOverScrollMode(View.OVER_SCROLL_NEVER);
        mWebView.setVerticalScrollBarEnabled(false);
        mWebView.setHorizontalScrollBarEnabled(false);

        setupWebSettings(mWebView.getSettings());
        mWebView.addJavascriptInterface(new WebAppInterface(), "AndroidBridge");
        setupWebViewClients();

        mSwipeRefreshLayout.addView(mWebView);
        mSwipeRefreshLayout.setOnRefreshListener(() -> navigateToUrl(mCurrentTargetUrl));
        mSwipeRefreshLayout.setOnChildScrollUpCallback((parent, child) -> mWebView != null && mWebView.getScrollY() > 0);

        mRootContainer.addView(mSwipeRefreshLayout);

        // --- 2. Native Loading View ---
        mLoadingView = createLoadingView();
        mRootContainer.addView(mLoadingView);

        // --- 3. Native Error & Diagnostics View ---
        mErrorView = createErrorView();
        mRootContainer.addView(mErrorView);

        // Initial State
        setAppState(STATE_LOADING);
    }

    private void setupWebSettings(WebSettings settings) {
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setAllowFileAccessFromFileURLs(true);
        settings.setAllowUniversalAccessFromFileURLs(true);
        settings.setLoadWithOverviewMode(true);
        settings.setUseWideViewPort(true);
        settings.setTextZoom(100); // Stabilize font scaling
        settings.setCacheMode(WebSettings.LOAD_DEFAULT);
        settings.setMediaPlaybackRequiresUserGesture(false);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        }

        String defaultUA = settings.getUserAgentString();
        settings.setUserAgentString(defaultUA + " CalorieCastNative/1.0");
    }

    private void setupWebViewClients() {
        mWebView.setWebViewClient(new WebViewClient() {
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                if (mAssetLoader != null && request != null && request.getUrl() != null) {
                    WebResourceResponse response = mAssetLoader.shouldInterceptRequest(request.getUrl());
                    if (response != null) {
                        return response;
                    }
                }
                return super.shouldInterceptRequest(view, request);
            }

            @SuppressWarnings("deprecation")
            @Override
            public WebResourceResponse shouldInterceptRequest(WebView view, String url) {
                if (mAssetLoader != null && url != null) {
                    WebResourceResponse response = mAssetLoader.shouldInterceptRequest(Uri.parse(url));
                    if (response != null) {
                        return response;
                    }
                }
                return super.shouldInterceptRequest(view, url);
            }

            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                String url = request.getUrl().toString();
                if (url.startsWith("http://") || url.startsWith("https://")) {
                    return false; // Render in-app
                }
                try {
                    Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                    startActivity(intent);
                    return true;
                } catch (Exception e) {
                    return true;
                }
            }

            @Override
            public void onPageStarted(WebView view, String url, Bitmap favicon) {
                super.onPageStarted(view, url, favicon);
                mHasPageError = false;
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                mSwipeRefreshLayout.setRefreshing(false);
                cancelWatchdog();

                // If an error occurred during loading, do NOT switch to content view
                if (mHasPageError) {
                    return;
                }

                if (url != null && !url.equals("about:blank")) {
                    mPageLoadedSuccessfully = true;
                    setAppState(STATE_CONTENT);
                }
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                super.onReceivedError(view, request, error);
                if (request != null && request.isForMainFrame()) {
                    String desc = "Network unreachable";
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M && error != null) {
                        desc = String.valueOf(error.getDescription());
                    }
                    handlePageError(request.getUrl().toString(), desc);
                }
            }

            @SuppressWarnings("deprecation")
            @Override
            public void onReceivedError(WebView view, int errorCode, String description, String failingUrl) {
                super.onReceivedError(view, errorCode, description, failingUrl);
                handlePageError(failingUrl, description);
            }

            @Override
            public void onReceivedHttpError(WebView view, WebResourceRequest request, WebResourceResponse errorResponse) {
                super.onReceivedHttpError(view, request, errorResponse);
                if (request != null && request.isForMainFrame()) {
                    int statusCode = errorResponse != null ? errorResponse.getStatusCode() : 500;
                    handlePageError(request.getUrl().toString(), "HTTP " + statusCode + " Server Error");
                }
            }
        });

        mWebView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView webView, ValueCallback<Uri[]> filePathCallback, FileChooserParams fileChooserParams) {
                if (mFilePathCallback != null) {
                    mFilePathCallback.onReceiveValue(null);
                }
                mFilePathCallback = filePathCallback;

                Intent intent = fileChooserParams.createIntent();
                try {
                    startActivityForResult(intent, FILE_CHOOSER_RESULT_CODE);
                } catch (Exception e) {
                    mFilePathCallback = null;
                    Toast.makeText(MainActivity.this, "Cannot open camera/gallery", Toast.LENGTH_SHORT).show();
                    return false;
                }
                return true;
            }

            @Override
            public void onPermissionRequest(PermissionRequest request) {
                request.grant(request.getResources());
            }
        });
    }

    private void handlePageError(String failingUrl, String desc) {
        cancelWatchdog();
        mHasPageError = true;
        mPageLoadedSuccessfully = false;
        mSwipeRefreshLayout.setRefreshing(false);
        showErrorState("Could not connect to server (" + desc + ")");
    }

    /**
     * Builds the Native Loading / Splash View
     */
    private LinearLayout createLoadingView() {
        LinearLayout layout = new LinearLayout(this);
        layout.setLayoutParams(new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setGravity(Gravity.CENTER);
        layout.setBackgroundColor(0xFF0F172A);
        layout.setPadding(dpToPx(24), dpToPx(24), dpToPx(24), dpToPx(24));

        TextView logoView = new TextView(this);
        logoView.setText("🔥");
        logoView.setTextSize(TypedValue.COMPLEX_UNIT_SP, 56);
        logoView.setGravity(Gravity.CENTER);
        layout.addView(logoView);

        TextView titleView = new TextView(this);
        titleView.setText("CalorieCast");
        titleView.setTextSize(TypedValue.COMPLEX_UNIT_SP, 28);
        titleView.setTextColor(0xFF38BDF8); // Accent color
        titleView.setTypeface(Typeface.DEFAULT_BOLD);
        titleView.setGravity(Gravity.CENTER);
        titleView.setPadding(0, dpToPx(8), 0, dpToPx(4));
        layout.addView(titleView);

        TextView subtitleView = new TextView(this);
        subtitleView.setText("AI Fitness & Nutrition Engine");
        subtitleView.setTextSize(TypedValue.COMPLEX_UNIT_SP, 14);
        subtitleView.setTextColor(0xFF94A3B8);
        subtitleView.setGravity(Gravity.CENTER);
        subtitleView.setPadding(0, 0, 0, dpToPx(32));
        layout.addView(subtitleView);

        ProgressBar progressBar = new ProgressBar(this);
        progressBar.setLayoutParams(new LinearLayout.LayoutParams(dpToPx(48), dpToPx(48)));
        layout.addView(progressBar);

        mLoadingStatusText = new TextView(this);
        mLoadingStatusText.setText("Starting CalorieCast...");
        mLoadingStatusText.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13);
        mLoadingStatusText.setTextColor(0xFF64748B);
        mLoadingStatusText.setGravity(Gravity.CENTER);
        mLoadingStatusText.setPadding(0, dpToPx(16), 0, 0);
        layout.addView(mLoadingStatusText);

        return layout;
    }

    /**
     * Builds the Native Connection Error & Diagnostics View
     */
    private ScrollView createErrorView() {
        ScrollView scrollView = new ScrollView(this);
        scrollView.setLayoutParams(new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));
        scrollView.setBackgroundColor(0xFF0F172A);
        scrollView.setFillViewport(true);

        LinearLayout cardContainer = new LinearLayout(this);
        cardContainer.setLayoutParams(new ScrollView.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        cardContainer.setOrientation(LinearLayout.VERTICAL);
        cardContainer.setGravity(Gravity.CENTER_HORIZONTAL);
        cardContainer.setPadding(dpToPx(20), dpToPx(36), dpToPx(20), dpToPx(36));

        LinearLayout card = new LinearLayout(this);
        LinearLayout.LayoutParams cardParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        card.setLayoutParams(cardParams);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dpToPx(24), dpToPx(24), dpToPx(24), dpToPx(24));

        GradientDrawable cardBg = new GradientDrawable();
        cardBg.setColor(0xFF1E293B);
        cardBg.setCornerRadius(dpToPx(16));
        cardBg.setStroke(dpToPx(1), 0xFF334155);
        card.setBackground(cardBg);

        TextView headerTitle = new TextView(this);
        headerTitle.setText("⚠️ Unable to Reach Server");
        headerTitle.setTextSize(TypedValue.COMPLEX_UNIT_SP, 20);
        headerTitle.setTextColor(0xFFF59E0B);
        headerTitle.setTypeface(Typeface.DEFAULT_BOLD);
        headerTitle.setGravity(Gravity.CENTER);
        headerTitle.setPadding(0, 0, 0, dpToPx(10));
        card.addView(headerTitle);

        mErrorDetailText = new TextView(this);
        mErrorDetailText.setText("Could not reach backend server. You can launch the embedded offline app or configure your PC IP.");
        mErrorDetailText.setTextSize(TypedValue.COMPLEX_UNIT_SP, 13);
        mErrorDetailText.setTextColor(0xFF94A3B8);
        mErrorDetailText.setGravity(Gravity.CENTER);
        mErrorDetailText.setPadding(0, 0, 0, dpToPx(16));
        card.addView(mErrorDetailText);

        // Primary Button: Launch Local Embedded App
        Button btnLaunchLocal = createStyledButton("📱 Launch Embedded App (Offline)", 0xFF38BDF8, 0xFF0F172A, true);
        btnLaunchLocal.setOnClickListener(v -> navigateToUrl(LOCAL_APP_URL));
        card.addView(btnLaunchLocal);

        TextView label = new TextView(this);
        label.setText("Backend Host Address (IP:Port):");
        label.setTextSize(TypedValue.COMPLEX_UNIT_SP, 12);
        label.setTextColor(0xFF94A3B8);
        label.setTypeface(Typeface.DEFAULT_BOLD);
        label.setPadding(0, dpToPx(16), 0, dpToPx(6));
        card.addView(label);

        mServerAddressInput = new EditText(this);
        mServerAddressInput.setLayoutParams(new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        mServerAddressInput.setText(DEFAULT_DEV_IP);
        mServerAddressInput.setTextColor(0xFF38BDF8);
        mServerAddressInput.setTextSize(TypedValue.COMPLEX_UNIT_SP, 15);
        mServerAddressInput.setGravity(Gravity.CENTER);
        mServerAddressInput.setSingleLine(true);
        mServerAddressInput.setPadding(dpToPx(12), dpToPx(12), dpToPx(12), dpToPx(12));

        GradientDrawable inputBg = new GradientDrawable();
        inputBg.setColor(0xFF0F172A);
        inputBg.setCornerRadius(dpToPx(8));
        inputBg.setStroke(dpToPx(1), 0xFF475569);
        mServerAddressInput.setBackground(inputBg);
        card.addView(mServerAddressInput);

        Button btnRetry = createStyledButton("🔄 Update Server & Reconnect", 0xFF334155, 0xFFF8FAFC, false);
        LinearLayout.LayoutParams retryParams = (LinearLayout.LayoutParams) btnRetry.getLayoutParams();
        retryParams.setMargins(0, dpToPx(12), 0, dpToPx(16));
        btnRetry.setOnClickListener(v -> {
            String entered = mServerAddressInput.getText().toString().trim();
            updateServerAndReload(entered);
        });
        card.addView(btnRetry);

        TextView presetsHeader = new TextView(this);
        presetsHeader.setText("Quick Network Presets:");
        presetsHeader.setTextSize(TypedValue.COMPLEX_UNIT_SP, 12);
        presetsHeader.setTextColor(0xFF64748B);
        presetsHeader.setTypeface(Typeface.DEFAULT_BOLD);
        presetsHeader.setPadding(0, 0, 0, dpToPx(6));
        card.addView(presetsHeader);

        Button btnPresetWifi = createPresetButton("📶 Wi-Fi PC IP (" + DEFAULT_DEV_IP + ")", DEFAULT_DEV_IP);
        card.addView(btnPresetWifi);

        Button btnPresetUsb = createPresetButton("🔌 USB Reverse Tether (127.0.0.1:8000)", "127.0.0.1:8000");
        card.addView(btnPresetUsb);

        Button btnPresetEmu = createPresetButton("💻 Android Emulator (10.0.2.2:8000)", "10.0.2.2:8000");
        card.addView(btnPresetEmu);

        mDiagnosticsText = new TextView(this);
        mDiagnosticsText.setTextSize(TypedValue.COMPLEX_UNIT_SP, 11);
        mDiagnosticsText.setTextColor(0xFF94A3B8);
        mDiagnosticsText.setPadding(dpToPx(12), dpToPx(12), dpToPx(12), dpToPx(12));
        mDiagnosticsText.setBackgroundColor(0xFF0F172A);

        GradientDrawable diagBg = new GradientDrawable();
        diagBg.setColor(0xFF0F172A);
        diagBg.setCornerRadius(dpToPx(8));
        diagBg.setStroke(dpToPx(1), 0xFF334155);
        mDiagnosticsText.setBackground(diagBg);

        LinearLayout.LayoutParams diagParams = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        diagParams.setMargins(0, dpToPx(14), 0, 0);
        mDiagnosticsText.setLayoutParams(diagParams);
        card.addView(mDiagnosticsText);

        cardContainer.addView(card);
        scrollView.addView(cardContainer);
        return scrollView;
    }

    private Button createStyledButton(String text, int bgColor, int textColor, boolean isPrimary) {
        Button btn = new Button(this);
        btn.setLayoutParams(new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dpToPx(48)));
        btn.setText(text);
        btn.setTextColor(textColor);
        btn.setTextSize(TypedValue.COMPLEX_UNIT_SP, 14);
        btn.setTypeface(Typeface.DEFAULT_BOLD);

        GradientDrawable bg = new GradientDrawable();
        bg.setColor(bgColor);
        bg.setCornerRadius(dpToPx(8));
        btn.setBackground(bg);
        return btn;
    }

    private Button createPresetButton(String label, final String targetAddress) {
        Button btn = new Button(this);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, dpToPx(40));
        params.setMargins(0, dpToPx(3), 0, dpToPx(3));
        btn.setLayoutParams(params);
        btn.setText(label);
        btn.setTextColor(0xFFCBD5E1);
        btn.setTextSize(TypedValue.COMPLEX_UNIT_SP, 12);
        btn.setGravity(Gravity.CENTER_VERTICAL | Gravity.START);
        btn.setPadding(dpToPx(12), 0, dpToPx(12), 0);

        GradientDrawable bg = new GradientDrawable();
        bg.setColor(0xFF334155);
        bg.setCornerRadius(dpToPx(6));
        btn.setBackground(bg);

        btn.setOnClickListener(v -> {
            mServerAddressInput.setText(targetAddress);
            updateServerAndReload(targetAddress);
        });
        return btn;
    }

    private void setAppState(int state) {
        mMainHandler.post(() -> {
            if (state == STATE_LOADING) {
                mLoadingView.setVisibility(View.VISIBLE);
                mSwipeRefreshLayout.setVisibility(View.GONE);
                mErrorView.setVisibility(View.GONE);
            } else if (state == STATE_CONTENT) {
                mLoadingView.setVisibility(View.GONE);
                mSwipeRefreshLayout.setVisibility(View.VISIBLE);
                mErrorView.setVisibility(View.GONE);
            } else if (state == STATE_ERROR) {
                mLoadingView.setVisibility(View.GONE);
                mSwipeRefreshLayout.setVisibility(View.GONE);
                mErrorView.setVisibility(View.VISIBLE);
                updateDiagnosticsDisplay();
            }
        });
    }

    private void updateDiagnosticsDisplay() {
        ConnectivityManager cm = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
        NetworkInfo activeNet = cm != null ? cm.getActiveNetworkInfo() : null;
        boolean isConnected = activeNet != null && activeNet.isConnected();
        String netType = isConnected ? activeNet.getTypeName() : "None (Disconnected)";
        boolean isWifi = activeNet != null && activeNet.getType() == ConnectivityManager.TYPE_WIFI;

        StringBuilder sb = new StringBuilder();
        sb.append("Connection Diagnostics:\n");
        sb.append("• Target: ").append(mCurrentTargetUrl).append("\n");
        sb.append("• Network: ").append(netType).append(isConnected ? " (Online)" : " (Offline)").append("\n");

        if (!isWifi) {
            sb.append("\n⚠️ Phone is NOT on Wi-Fi. Private IP requires phone & laptop on same Wi-Fi.\n");
        } else {
            sb.append("• Wi-Fi Status: Connected to local Wi-Fi.\n");
        }

        sb.append("\nTips:\n");
        sb.append("1. Tap 'Launch Embedded App' to use CalorieCast offline.\n");
        sb.append("2. Or connect phone & PC to same Wi-Fi with uvicorn running.\n");
        sb.append("3. Or connect USB cable and run: adb reverse tcp:8000 tcp:8000");

        if (mDiagnosticsText != null) {
            mDiagnosticsText.setText(sb.toString());
        }
    }

    private void navigateToUrl(String url) {
        mCurrentTargetUrl = url;
        mPageLoadedSuccessfully = false;
        mHasPageError = false;

        setAppState(STATE_LOADING);
        if (mLoadingStatusText != null) {
            mLoadingStatusText.setText("Loading CalorieCast...");
        }

        cancelWatchdog();
        mWatchdogRunnable = () -> {
            if (!mPageLoadedSuccessfully) {
                handlePageError(mCurrentTargetUrl, "Connection timed out");
            }
        };
        mMainHandler.postDelayed(mWatchdogRunnable, WATCHDOG_TIMEOUT_MS);

        mWebView.loadUrl(mCurrentTargetUrl);
    }

    private void showErrorState(String reason) {
        if (mErrorDetailText != null) {
            mErrorDetailText.setText(reason);
        }
        if (mServerAddressInput != null) {
            mServerAddressInput.setText(extractHost(getSavedServerAddress()));
        }
        setAppState(STATE_ERROR);
    }

    private void updateServerAndReload(String rawAddress) {
        if (rawAddress == null || rawAddress.trim().isEmpty()) {
            Toast.makeText(this, "Please enter a valid server address", Toast.LENGTH_SHORT).show();
            return;
        }

        saveServerAddress(rawAddress);
        Toast.makeText(this, "Updated backend server address", Toast.LENGTH_SHORT).show();
        navigateToUrl(LOCAL_APP_URL);
    }

    private void cancelWatchdog() {
        if (mWatchdogRunnable != null) {
            mMainHandler.removeCallbacks(mWatchdogRunnable);
            mWatchdogRunnable = null;
        }
    }

    private String getSavedServerAddress() {
        SharedPreferences prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        return prefs.getString(KEY_SERVER_ADDRESS, DEFAULT_BACKEND_URL);
    }

    private void saveServerAddress(String raw) {
        String clean = raw.trim();
        if (!clean.startsWith("http://") && !clean.startsWith("https://")) {
            clean = "http://" + clean;
        }
        try {
            Uri uri = Uri.parse(clean);
            String host = uri.getHost();
            int port = uri.getPort();
            String scheme = uri.getScheme() != null ? uri.getScheme() : "http";
            if (host != null) {
                clean = scheme + "://" + host + (port > 0 ? (":" + port) : "");
            }
        } catch (Exception ignored) {}

        SharedPreferences prefs = getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        prefs.edit().putString(KEY_SERVER_ADDRESS, clean).apply();
    }

    private String extractHost(String url) {
        try {
            Uri uri = Uri.parse(url);
            String host = uri.getHost();
            int port = uri.getPort();
            if (host != null) {
                return port > 0 ? (host + ":" + port) : host;
            }
        } catch (Exception ignored) {}
        return url;
    }

    private int dpToPx(int dp) {
        return (int) (dp * getResources().getDisplayMetrics().density + 0.5f);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        if (requestCode == FILE_CHOOSER_RESULT_CODE) {
            if (mFilePathCallback == null) return;
            Uri[] results = null;
            if (resultCode == Activity.RESULT_OK && data != null) {
                String dataString = data.getDataString();
                if (dataString != null) {
                    results = new Uri[]{Uri.parse(dataString)};
                }
            }
            mFilePathCallback.onReceiveValue(results);
            mFilePathCallback = null;
        } else {
            super.onActivityResult(requestCode, resultCode, data);
        }
    }

    @Override
    public void onBackPressed() {
        if (mErrorView != null && mErrorView.getVisibility() == View.VISIBLE) {
            navigateToUrl(LOCAL_APP_URL);
            return;
        }

        if (mWebView != null && mWebView.canGoBack()) {
            mWebView.goBack();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onDestroy() {
        cancelWatchdog();
        if (mWebView != null) {
            mWebView.destroy();
        }
        super.onDestroy();
    }
}
