package com.verlox.carinakeprix.app.protocol

import org.junit.Assert.assertEquals
import org.junit.Test

class CarinaProtocolConstantsTest {
  @Test
  fun canvasCommandsUseStableStrings() {
    assertEquals("canvas.present", CarinaCanvasCommand.Present.rawValue)
    assertEquals("canvas.hide", CarinaCanvasCommand.Hide.rawValue)
    assertEquals("canvas.navigate", CarinaCanvasCommand.Navigate.rawValue)
    assertEquals("canvas.eval", CarinaCanvasCommand.Eval.rawValue)
    assertEquals("canvas.snapshot", CarinaCanvasCommand.Snapshot.rawValue)
  }

  @Test
  fun a2uiCommandsUseStableStrings() {
    assertEquals("canvas.a2ui.push", CarinaCanvasA2UICommand.Push.rawValue)
    assertEquals("canvas.a2ui.pushJSONL", CarinaCanvasA2UICommand.PushJSONL.rawValue)
    assertEquals("canvas.a2ui.reset", CarinaCanvasA2UICommand.Reset.rawValue)
  }

  @Test
  fun capabilitiesUseStableStrings() {
    assertEquals("canvas", CarinaCapability.Canvas.rawValue)
    assertEquals("camera", CarinaCapability.Camera.rawValue)
    assertEquals("voiceWake", CarinaCapability.VoiceWake.rawValue)
    assertEquals("talk", CarinaCapability.Talk.rawValue)
    assertEquals("location", CarinaCapability.Location.rawValue)
    assertEquals("sms", CarinaCapability.Sms.rawValue)
    assertEquals("device", CarinaCapability.Device.rawValue)
    assertEquals("notifications", CarinaCapability.Notifications.rawValue)
    assertEquals("system", CarinaCapability.System.rawValue)
    assertEquals("photos", CarinaCapability.Photos.rawValue)
    assertEquals("contacts", CarinaCapability.Contacts.rawValue)
    assertEquals("calendar", CarinaCapability.Calendar.rawValue)
    assertEquals("motion", CarinaCapability.Motion.rawValue)
    assertEquals("callLog", CarinaCapability.CallLog.rawValue)
  }

  @Test
  fun cameraCommandsUseStableStrings() {
    assertEquals("camera.list", CarinaCameraCommand.List.rawValue)
    assertEquals("camera.snap", CarinaCameraCommand.Snap.rawValue)
    assertEquals("camera.clip", CarinaCameraCommand.Clip.rawValue)
  }

  @Test
  fun notificationsCommandsUseStableStrings() {
    assertEquals("notifications.list", CarinaNotificationsCommand.List.rawValue)
    assertEquals("notifications.actions", CarinaNotificationsCommand.Actions.rawValue)
  }

  @Test
  fun deviceCommandsUseStableStrings() {
    assertEquals("device.status", CarinaDeviceCommand.Status.rawValue)
    assertEquals("device.info", CarinaDeviceCommand.Info.rawValue)
    assertEquals("device.permissions", CarinaDeviceCommand.Permissions.rawValue)
    assertEquals("device.health", CarinaDeviceCommand.Health.rawValue)
    assertEquals("device.apps", CarinaDeviceCommand.Apps.rawValue)
  }

  @Test
  fun systemCommandsUseStableStrings() {
    assertEquals("system.notify", CarinaSystemCommand.Notify.rawValue)
  }

  @Test
  fun photosCommandsUseStableStrings() {
    assertEquals("photos.latest", CarinaPhotosCommand.Latest.rawValue)
  }

  @Test
  fun contactsCommandsUseStableStrings() {
    assertEquals("contacts.search", CarinaContactsCommand.Search.rawValue)
    assertEquals("contacts.add", CarinaContactsCommand.Add.rawValue)
  }

  @Test
  fun calendarCommandsUseStableStrings() {
    assertEquals("calendar.events", CarinaCalendarCommand.Events.rawValue)
    assertEquals("calendar.add", CarinaCalendarCommand.Add.rawValue)
  }

  @Test
  fun motionCommandsUseStableStrings() {
    assertEquals("motion.activity", CarinaMotionCommand.Activity.rawValue)
    assertEquals("motion.pedometer", CarinaMotionCommand.Pedometer.rawValue)
  }

  @Test
  fun smsCommandsUseStableStrings() {
    assertEquals("sms.send", CarinaSmsCommand.Send.rawValue)
    assertEquals("sms.search", CarinaSmsCommand.Search.rawValue)
  }

  @Test
  fun talkCommandsUseStableStrings() {
    assertEquals("talk.ptt.start", CarinaTalkCommand.PttStart.rawValue)
    assertEquals("talk.ptt.stop", CarinaTalkCommand.PttStop.rawValue)
    assertEquals("talk.ptt.cancel", CarinaTalkCommand.PttCancel.rawValue)
    assertEquals("talk.ptt.once", CarinaTalkCommand.PttOnce.rawValue)
  }

  @Test
  fun callLogCommandsUseStableStrings() {
    assertEquals("callLog.search", CarinaCallLogCommand.Search.rawValue)
  }
}
