package com.archit.pix_glance

import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.OpenableColumns
import android.webkit.MimeTypeMap
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import java.io.File

class MainActivity : FlutterActivity() {
    private val channelName = "app.channel.shared.data"
    private var channel: MethodChannel? = null

    // Path from the intent that launched us (cold start). Dart pulls this once on startup.
    private var pendingPath: String? = null

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        channel = MethodChannel(flutterEngine.dartExecutor.binaryMessenger, channelName).also { ch ->
            ch.setMethodCallHandler { call, result ->
                when (call.method) {
                    "getSharedData" -> {
                        result.success(pendingPath)
                        pendingPath = null
                    }
                    else -> result.notImplemented()
                }
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // Cold start: stash the path, Dart will pull it with getSharedData.
        // (Dart's handler isn't registered yet, so pushing here would be dropped.)
        if (savedInstanceState == null) {
            pendingPath = extractPath(intent)
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        // Warm start: Dart is already running, so push the path to it.
        extractPath(intent)?.let { path ->
            channel?.invokeMethod("onNewFile", path)
        }
    }

    private fun extractPath(intent: Intent?): String? {
        if (intent == null) return null
        val uri: Uri? = when (intent.action) {
            Intent.ACTION_VIEW -> intent.data
            Intent.ACTION_SEND -> {
                if (Build.VERSION.SDK_INT >= 33) {
                    intent.getParcelableExtra(Intent.EXTRA_STREAM, Uri::class.java)
                } else {
                    @Suppress("DEPRECATION")
                    intent.getParcelableExtra(Intent.EXTRA_STREAM)
                }
            }
            else -> null
        }
        return uri?.let { getFilePathFromUri(it) }
    }

    private fun getFilePathFromUri(uri: Uri): String? {
        return when (uri.scheme) {
            "file" -> uri.path
            "content" -> copyContentUri(uri)
            else -> null
        }
    }

    private fun copyContentUri(uri: Uri): String? {
        return try {
            val dir = File(cacheDir, "incoming").apply { mkdirs() }
            val outFile = File(dir, buildFileName(uri))
            contentResolver.openInputStream(uri)?.use { input ->
                outFile.outputStream().use { output -> input.copyTo(output) }
            } ?: return null
            outFile.absolutePath
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }

    private fun buildFileName(uri: Uri): String {
        var name: String? = null
        contentResolver.query(uri, null, null, null, null)?.use { cursor ->
            if (cursor.moveToFirst()) {
                val idx = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                if (idx != -1) name = cursor.getString(idx)
            }
        }

        // Strip path separators so a hostile display name can't escape the folder.
        var safe = (name ?: "temp_image").replace(Regex("[\\\\/:*?\"<>|]"), "_").ifBlank { "temp_image" }

        // The Dart side decides SVG vs raster by extension, so make sure there is one.
        if (!safe.contains('.')) {
            val mime = contentResolver.getType(uri)
            val ext = when (mime) {
                "image/svg+xml" -> "svg"
                null -> null
                else -> MimeTypeMap.getSingleton().getExtensionFromMimeType(mime)
            }
            if (ext != null) safe = "$safe.$ext"
        }
        return safe
    }
}
