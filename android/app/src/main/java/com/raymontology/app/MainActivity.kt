package com.raymontology.app

import android.annotation.SuppressLint
import android.content.Intent
import android.graphics.Bitmap
import android.net.Uri
import android.os.Bundle
import android.view.KeyEvent
import android.view.View
import android.webkit.*
import android.widget.ProgressBar
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout

/**
 * Raymontology WebView App
 *
 * Main activity that displays the Raymontology web application
 * in a full-screen WebView with native-like experience.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private lateinit var progressBar: ProgressBar
    private lateinit var swipeRefresh: SwipeRefreshLayout
    private lateinit var errorView: View

    companion object {
        private const val WEBAPP_URL = BuildConfig.WEBAPP_URL
        private const val TAG = "RaymontologyApp"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        initViews()
        setupWebView()
        loadWebApp(savedInstanceState)
    }

    private fun initViews() {
        webView = findViewById(R.id.webView)
        progressBar = findViewById(R.id.progressBar)
        swipeRefresh = findViewById(R.id.swipeRefresh)
        errorView = findViewById(R.id.errorView)

        // Setup swipe to refresh
        swipeRefresh.setOnRefreshListener {
            webView.reload()
        }

        // Retry button in error view
        findViewById<View>(R.id.retryButton)?.setOnClickListener {
            errorView.visibility = View.GONE
            webView.visibility = View.VISIBLE
            webView.loadUrl(WEBAPP_URL)
        }
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun setupWebView() {
        webView.webViewClient = RaymontologyWebViewClient()
        webView.webChromeClient = RaymontologyWebChromeClient()

        webView.settings.apply {
            // Enable JavaScript (required for React app)
            javaScriptEnabled = true

            // Enable DOM storage (localStorage, sessionStorage)
            domStorageEnabled = true

            // Enable database storage
            databaseEnabled = true

            // Cache settings
            cacheMode = WebSettings.LOAD_DEFAULT

            // Display settings
            loadWithOverviewMode = true
            useWideViewPort = true

            // Zoom settings
            setSupportZoom(true)
            builtInZoomControls = true
            displayZoomControls = false

            // Text settings
            textZoom = 100

            // Security settings
            allowFileAccess = false
            allowContentAccess = false

            // Mixed content (allow HTTPS to load from HTTPS only)
            mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW

            // User agent (optional: add app identifier)
            userAgentString = "$userAgentString RaymontologyApp/${BuildConfig.VERSION_NAME}"
        }

        // Enable remote debugging in debug builds
        WebView.setWebContentsDebuggingEnabled(BuildConfig.DEBUG)
    }

    private fun loadWebApp(savedInstanceState: Bundle?) {
        if (savedInstanceState != null) {
            webView.restoreState(savedInstanceState)
        } else {
            // Check for deep link
            val deepLinkUrl = intent?.data?.toString()
            val urlToLoad = if (deepLinkUrl?.startsWith(WEBAPP_URL) == true) {
                deepLinkUrl
            } else {
                WEBAPP_URL
            }
            webView.loadUrl(urlToLoad)
        }
    }

    /**
     * Custom WebViewClient for handling page navigation
     */
    private inner class RaymontologyWebViewClient : WebViewClient() {

        override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {
            super.onPageStarted(view, url, favicon)
            progressBar.visibility = View.VISIBLE
            errorView.visibility = View.GONE
        }

        override fun onPageFinished(view: WebView?, url: String?) {
            super.onPageFinished(view, url)
            progressBar.visibility = View.GONE
            swipeRefresh.isRefreshing = false
        }

        override fun onReceivedError(
            view: WebView?,
            request: WebResourceRequest?,
            error: WebResourceError?
        ) {
            super.onReceivedError(view, request, error)
            // Only show error for main frame
            if (request?.isForMainFrame == true) {
                webView.visibility = View.GONE
                errorView.visibility = View.VISIBLE
                progressBar.visibility = View.GONE
                swipeRefresh.isRefreshing = false
            }
        }

        override fun shouldOverrideUrlLoading(
            view: WebView?,
            request: WebResourceRequest?
        ): Boolean {
            val url = request?.url?.toString() ?: return false

            // Keep navigation within the app for our domain
            if (url.startsWith(WEBAPP_URL) || url.startsWith("https://raymontology")) {
                return false
            }

            // Open external links in browser
            try {
                val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                startActivity(intent)
            } catch (e: Exception) {
                Toast.makeText(this@MainActivity, "Cannot open link", Toast.LENGTH_SHORT).show()
            }
            return true
        }
    }

    /**
     * Custom WebChromeClient for handling JavaScript dialogs and progress
     */
    private inner class RaymontologyWebChromeClient : WebChromeClient() {

        override fun onProgressChanged(view: WebView?, newProgress: Int) {
            super.onProgressChanged(view, newProgress)
            progressBar.progress = newProgress
        }

        override fun onJsAlert(
            view: WebView?,
            url: String?,
            message: String?,
            result: JsResult?
        ): Boolean {
            // Handle JavaScript alerts with native dialog
            Toast.makeText(this@MainActivity, message, Toast.LENGTH_LONG).show()
            result?.confirm()
            return true
        }
    }

    /**
     * Handle back button press - navigate WebView history
     */
    override fun onKeyDown(keyCode: Int, event: KeyEvent?): Boolean {
        if (keyCode == KeyEvent.KEYCODE_BACK && webView.canGoBack()) {
            webView.goBack()
            return true
        }
        return super.onKeyDown(keyCode, event)
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        webView.saveState(outState)
    }

    override fun onResume() {
        super.onResume()
        webView.onResume()
    }

    override fun onPause() {
        super.onPause()
        webView.onPause()
    }

    override fun onDestroy() {
        webView.destroy()
        super.onDestroy()
    }
}
