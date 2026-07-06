package com.verlox.carinakeprix.app.ui

import com.verlox.carinakeprix.app.MainViewModel
import com.verlox.carinakeprix.app.ui.chat.ChatSheetContent
import androidx.compose.runtime.Composable

/** Keeps the public shell entry point stable while chat internals live under ui.chat. */
@Composable
fun ChatSheet(viewModel: MainViewModel) {
  ChatSheetContent(viewModel = viewModel)
}
