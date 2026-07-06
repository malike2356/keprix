package com.verlox.carinakeprix.app.node

import com.verlox.carinakeprix.app.protocol.CarinaCalendarCommand
import com.verlox.carinakeprix.app.protocol.CarinaCallLogCommand
import com.verlox.carinakeprix.app.protocol.CarinaCameraCommand
import com.verlox.carinakeprix.app.protocol.CarinaCapability
import com.verlox.carinakeprix.app.protocol.CarinaContactsCommand
import com.verlox.carinakeprix.app.protocol.CarinaDeviceCommand
import com.verlox.carinakeprix.app.protocol.CarinaLocationCommand
import com.verlox.carinakeprix.app.protocol.CarinaMotionCommand
import com.verlox.carinakeprix.app.protocol.CarinaNotificationsCommand
import com.verlox.carinakeprix.app.protocol.CarinaPhotosCommand
import com.verlox.carinakeprix.app.protocol.CarinaSmsCommand
import com.verlox.carinakeprix.app.protocol.CarinaSystemCommand
import com.verlox.carinakeprix.app.protocol.CarinaTalkCommand
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class InvokeCommandRegistryTest {
  private val coreCapabilities =
    setOf(
      CarinaCapability.Canvas.rawValue,
      CarinaCapability.Device.rawValue,
      CarinaCapability.Notifications.rawValue,
      CarinaCapability.System.rawValue,
      CarinaCapability.Talk.rawValue,
      CarinaCapability.Contacts.rawValue,
      CarinaCapability.Calendar.rawValue,
    )

  private val optionalCapabilities =
    setOf(
      CarinaCapability.Camera.rawValue,
      CarinaCapability.Location.rawValue,
      CarinaCapability.Sms.rawValue,
      CarinaCapability.CallLog.rawValue,
      CarinaCapability.VoiceWake.rawValue,
      CarinaCapability.Motion.rawValue,
      CarinaCapability.Photos.rawValue,
    )

  private val coreCommands =
    setOf(
      CarinaDeviceCommand.Status.rawValue,
      CarinaDeviceCommand.Info.rawValue,
      CarinaDeviceCommand.Permissions.rawValue,
      CarinaDeviceCommand.Health.rawValue,
      CarinaNotificationsCommand.List.rawValue,
      CarinaNotificationsCommand.Actions.rawValue,
      CarinaSystemCommand.Notify.rawValue,
      CarinaTalkCommand.PttStart.rawValue,
      CarinaTalkCommand.PttStop.rawValue,
      CarinaTalkCommand.PttCancel.rawValue,
      CarinaTalkCommand.PttOnce.rawValue,
      CarinaContactsCommand.Search.rawValue,
      CarinaContactsCommand.Add.rawValue,
      CarinaCalendarCommand.Events.rawValue,
      CarinaCalendarCommand.Add.rawValue,
    )

  private val optionalCommands =
    setOf(
      CarinaCameraCommand.Snap.rawValue,
      CarinaCameraCommand.Clip.rawValue,
      CarinaCameraCommand.List.rawValue,
      CarinaLocationCommand.Get.rawValue,
      CarinaMotionCommand.Activity.rawValue,
      CarinaMotionCommand.Pedometer.rawValue,
      CarinaSmsCommand.Send.rawValue,
      CarinaSmsCommand.Search.rawValue,
      CarinaCallLogCommand.Search.rawValue,
      CarinaPhotosCommand.Latest.rawValue,
    )

  private val debugCommands = setOf("debug.logs", "debug.ed25519")

  @Test
  fun advertisedCapabilities_respectsFeatureAvailability() {
    val capabilities = InvokeCommandRegistry.advertisedCapabilities(defaultFlags())

    assertContainsAll(capabilities, coreCapabilities)
    assertMissingAll(capabilities, optionalCapabilities)
  }

  @Test
  fun advertisedCapabilities_includesFeatureCapabilitiesWhenEnabled() {
    val capabilities =
      InvokeCommandRegistry.advertisedCapabilities(
        defaultFlags(
          cameraEnabled = true,
          locationEnabled = true,
          sendSmsAvailable = true,
          readSmsAvailable = true,
          smsSearchPossible = true,
          callLogAvailable = true,
          photosAvailable = true,
          voiceWakeEnabled = true,
          motionActivityAvailable = true,
          motionPedometerAvailable = true,
        ),
      )

    assertContainsAll(capabilities, coreCapabilities + optionalCapabilities)
  }

  @Test
  fun advertisedCommands_respectsFeatureAvailability() {
    val commands = InvokeCommandRegistry.advertisedCommands(defaultFlags())

    assertContainsAll(commands, coreCommands)
    assertMissingAll(commands, optionalCommands + debugCommands)
  }

  @Test
  fun advertisedCommands_includesDeviceAppsOnlyWhenUserOptedIn() {
    val disabled = InvokeCommandRegistry.advertisedCommands(defaultFlags(installedAppsSharingEnabled = false))
    val enabled = InvokeCommandRegistry.advertisedCommands(defaultFlags(installedAppsSharingEnabled = true))

    assertFalse(disabled.contains(CarinaDeviceCommand.Apps.rawValue))
    assertTrue(enabled.contains(CarinaDeviceCommand.Apps.rawValue))
  }

  @Test
  fun advertisedCommands_includesFeatureCommandsWhenEnabled() {
    val commands =
      InvokeCommandRegistry.advertisedCommands(
        defaultFlags(
          cameraEnabled = true,
          locationEnabled = true,
          sendSmsAvailable = true,
          readSmsAvailable = true,
          smsSearchPossible = true,
          callLogAvailable = true,
          photosAvailable = true,
          motionActivityAvailable = true,
          motionPedometerAvailable = true,
          debugBuild = true,
        ),
      )

    assertContainsAll(commands, coreCommands + optionalCommands + debugCommands)
  }

  @Test
  fun advertisedCommands_onlyIncludesSupportedMotionCommands() {
    val commands =
      InvokeCommandRegistry.advertisedCommands(
        NodeRuntimeFlags(
          cameraEnabled = false,
          locationEnabled = false,
          sendSmsAvailable = false,
          readSmsAvailable = false,
          smsSearchPossible = false,
          callLogAvailable = false,
          photosAvailable = false,
          voiceWakeEnabled = false,
          motionActivityAvailable = true,
          motionPedometerAvailable = false,
          installedAppsSharingEnabled = false,
          debugBuild = false,
        ),
      )

    assertTrue(commands.contains(CarinaMotionCommand.Activity.rawValue))
    assertFalse(commands.contains(CarinaMotionCommand.Pedometer.rawValue))
  }

  @Test
  fun advertisedCommands_splitsSmsSendAndSearchAvailability() {
    val readOnlyCommands =
      InvokeCommandRegistry.advertisedCommands(
        defaultFlags(readSmsAvailable = true, smsSearchPossible = true),
      )
    val sendOnlyCommands =
      InvokeCommandRegistry.advertisedCommands(
        defaultFlags(sendSmsAvailable = true),
      )
    val requestableSearchCommands =
      InvokeCommandRegistry.advertisedCommands(
        defaultFlags(smsSearchPossible = true),
      )

    assertTrue(readOnlyCommands.contains(CarinaSmsCommand.Search.rawValue))
    assertFalse(readOnlyCommands.contains(CarinaSmsCommand.Send.rawValue))
    assertTrue(sendOnlyCommands.contains(CarinaSmsCommand.Send.rawValue))
    assertFalse(sendOnlyCommands.contains(CarinaSmsCommand.Search.rawValue))
    assertTrue(requestableSearchCommands.contains(CarinaSmsCommand.Search.rawValue))
  }

  @Test
  fun advertisedCapabilities_includeSmsWhenEitherSmsPathIsAvailable() {
    val readOnlyCapabilities =
      InvokeCommandRegistry.advertisedCapabilities(
        defaultFlags(readSmsAvailable = true),
      )
    val sendOnlyCapabilities =
      InvokeCommandRegistry.advertisedCapabilities(
        defaultFlags(sendSmsAvailable = true),
      )
    val requestableSearchCapabilities =
      InvokeCommandRegistry.advertisedCapabilities(
        defaultFlags(smsSearchPossible = true),
      )

    assertTrue(readOnlyCapabilities.contains(CarinaCapability.Sms.rawValue))
    assertTrue(sendOnlyCapabilities.contains(CarinaCapability.Sms.rawValue))
    assertFalse(requestableSearchCapabilities.contains(CarinaCapability.Sms.rawValue))
  }

  @Test
  fun advertisedCommands_excludesCallLogWhenUnavailable() {
    val commands = InvokeCommandRegistry.advertisedCommands(defaultFlags(callLogAvailable = false))

    assertFalse(commands.contains(CarinaCallLogCommand.Search.rawValue))
  }

  @Test
  fun advertisedCapabilities_excludesCallLogWhenUnavailable() {
    val capabilities = InvokeCommandRegistry.advertisedCapabilities(defaultFlags(callLogAvailable = false))

    assertFalse(capabilities.contains(CarinaCapability.CallLog.rawValue))
  }

  @Test
  fun advertisedPhotosSurface_respectsFeatureAvailability() {
    val disabledFlags = defaultFlags(photosAvailable = false)
    val enabledFlags = defaultFlags(photosAvailable = true)

    assertFalse(InvokeCommandRegistry.advertisedCapabilities(disabledFlags).contains(CarinaCapability.Photos.rawValue))
    assertFalse(InvokeCommandRegistry.advertisedCommands(disabledFlags).contains(CarinaPhotosCommand.Latest.rawValue))
    assertTrue(InvokeCommandRegistry.advertisedCapabilities(enabledFlags).contains(CarinaCapability.Photos.rawValue))
    assertTrue(InvokeCommandRegistry.advertisedCommands(enabledFlags).contains(CarinaPhotosCommand.Latest.rawValue))
  }

  @Test
  fun advertisedCapabilities_includesVoiceWakeWithoutAdvertisingCommands() {
    val capabilities = InvokeCommandRegistry.advertisedCapabilities(defaultFlags(voiceWakeEnabled = true))
    val commands = InvokeCommandRegistry.advertisedCommands(defaultFlags(voiceWakeEnabled = true))

    assertTrue(capabilities.contains(CarinaCapability.VoiceWake.rawValue))
    assertFalse(commands.any { it.contains("voice", ignoreCase = true) })
  }

  @Test
  fun find_returnsForegroundMetadataForCameraCommands() {
    val list = InvokeCommandRegistry.find(CarinaCameraCommand.List.rawValue)
    val location = InvokeCommandRegistry.find(CarinaLocationCommand.Get.rawValue)

    assertNotNull(list)
    assertEquals(true, list?.requiresForeground)
    assertNotNull(location)
    assertEquals(false, location?.requiresForeground)
  }

  @Test
  fun find_returnsNullForUnknownCommand() {
    assertNull(InvokeCommandRegistry.find("not.real"))
  }

  private fun defaultFlags(
    cameraEnabled: Boolean = false,
    locationEnabled: Boolean = false,
    sendSmsAvailable: Boolean = false,
    readSmsAvailable: Boolean = false,
    smsSearchPossible: Boolean = false,
    callLogAvailable: Boolean = false,
    photosAvailable: Boolean = false,
    voiceWakeEnabled: Boolean = false,
    motionActivityAvailable: Boolean = false,
    motionPedometerAvailable: Boolean = false,
    installedAppsSharingEnabled: Boolean = false,
    debugBuild: Boolean = false,
  ): NodeRuntimeFlags =
    NodeRuntimeFlags(
      cameraEnabled = cameraEnabled,
      locationEnabled = locationEnabled,
      sendSmsAvailable = sendSmsAvailable,
      readSmsAvailable = readSmsAvailable,
      smsSearchPossible = smsSearchPossible,
      callLogAvailable = callLogAvailable,
      photosAvailable = photosAvailable,
      voiceWakeEnabled = voiceWakeEnabled,
      motionActivityAvailable = motionActivityAvailable,
      motionPedometerAvailable = motionPedometerAvailable,
      installedAppsSharingEnabled = installedAppsSharingEnabled,
      debugBuild = debugBuild,
    )

  private fun assertContainsAll(
    actual: List<String>,
    expected: Set<String>,
  ) {
    expected.forEach { value -> assertTrue(actual.contains(value)) }
  }

  private fun assertMissingAll(
    actual: List<String>,
    forbidden: Set<String>,
  ) {
    forbidden.forEach { value -> assertFalse(actual.contains(value)) }
  }
}
