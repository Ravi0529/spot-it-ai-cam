import React, { useState, useRef, useEffect } from "react";
import { View, Text, TouchableOpacity, Alert, Platform } from "react-native";
import { CameraView, Camera } from "expo-camera";
import { Ionicons } from "@expo/vector-icons";
import * as MediaLibrary from "expo-media-library";

export default function Index() {
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [time, setTime] = useState(0);
  const [cameraType, setCameraType] = useState<"back" | "front">("back");
  const [videoUri, setVideoUri] = useState<string | null>(null);
  const [isCameraReady, setIsCameraReady] = useState(false);
  const cameraRef = useRef<any>(null);
  const timerRef = useRef<number | NodeJS.Timeout | null>(null);
  const recordingStatusRef = useRef({
    isReady: false,
    startTime: 0,
    shouldStop: false,
  });

  useEffect(() => {
    (async () => {
      const { status } = await Camera.requestCameraPermissionsAsync();
      const micStatus = await Camera.requestMicrophonePermissionsAsync();
      const mediaStatus = await MediaLibrary.requestPermissionsAsync();
      setHasPermission(
        status === "granted" &&
          micStatus.status === "granted" &&
          mediaStatus.status === "granted"
      );
    })();

    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
      .toString()
      .padStart(2, "0");
    const secs = (seconds % 60).toString().padStart(2, "0");
    return `${mins}:${secs}`;
  };

  const startRecording = async () => {
    if (!cameraRef.current || !isCameraReady) {
      Alert.alert("Error", "Camera is not ready yet");
      return;
    }

    try {
      // Reset recording state
      recordingStatusRef.current = {
        isReady: false,
        startTime: Date.now(),
        shouldStop: false,
      };
      setIsRecording(true);
      setTime(0);

      // Start timer
      timerRef.current = setInterval(() => {
        setTime((t) => {
          // Auto-stop after 30 seconds
          if (t >= 29) {
            stopRecording();
          }
          return t + 1;
        });
      }, 1000);

      // Additional warm-up time for Android
      if (Platform.OS === "android") {
        await new Promise((resolve) => setTimeout(resolve, 500));
      }

      // Start recording
      const recordingPromise = cameraRef.current.recordAsync({
        quality: Platform.OS === "ios" ? "720p" : "480p",
        maxDuration: 30,
        mute: false,
      });

      // Mark recording as ready after sufficient time
      setTimeout(
        () => {
          recordingStatusRef.current.isReady = true;
          if (recordingStatusRef.current.shouldStop) {
            stopRecording();
          }
        },
        Platform.OS === "ios" ? 800 : 1500
      );

      const video = await recordingPromise;
      setVideoUri(video.uri);
      console.log("Recording completed successfully");
    } catch (error) {
      console.error("Recording error:", error);
      cleanupRecording();
      Alert.alert("Error", "Failed to start recording");
    }
  };

  const stopRecording = async () => {
    if (!isRecording) return;

    try {
      // Check if we should wait for recording to be ready
      if (!recordingStatusRef.current.isReady) {
        recordingStatusRef.current.shouldStop = true;
        return;
      }

      // Ensure minimum recording duration (1.5 seconds)
      const recordingDuration =
        Date.now() - recordingStatusRef.current.startTime;
      if (recordingDuration < 1500) {
        throw new Error("Recording too short");
      }

      // Stop recording
      if (cameraRef.current) {
        await cameraRef.current.stopRecording();
      }

      console.log("Recording stopped successfully");
      Alert.alert("Success", "Video recorded successfully!");
    } catch (error) {
      console.error("Error stopping recording:", error);
      Alert.alert("Failed to stop recording");
    } finally {
      cleanupRecording();
    }
  };

  const cleanupRecording = () => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setIsRecording(false);
    recordingStatusRef.current = {
      isReady: false,
      startTime: 0,
      shouldStop: false,
    };
  };

  const toggleCamera = () => {
    setCameraType((prev) => (prev === "back" ? "front" : "back"));
  };

  const resetRecording = () => {
    setVideoUri(null);
    setTime(0);
  };

  if (hasPermission === null) {
    return <View className="flex-1 bg-black" />;
  }

  if (hasPermission === false) {
    return (
      <View className="flex-1 items-center justify-center bg-white">
        <Text className="text-xl font-bold text-red-500">
          No access to camera or microphone
        </Text>
      </View>
    );
  }

  return (
    <View className="flex-1 bg-black">
      <CameraView
        ref={cameraRef}
        style={{ flex: 1 }}
        facing={cameraType}
        ratio="16:9"
        onCameraReady={() => setIsCameraReady(true)}
      />

      {isRecording && (
        <View className="absolute top-10 w-full items-center z-10">
          <View className="bg-black/50 px-4 py-2 rounded-full">
            <Text className="text-red-500 text-2xl font-bold">
              {formatTime(time)}
            </Text>
          </View>
        </View>
      )}

      <View className="absolute top-10 right-4 z-10">
        <TouchableOpacity
          onPress={toggleCamera}
          className="bg-black/50 rounded-full p-3"
          disabled={isRecording}
        >
          <Ionicons name="camera-reverse" size={24} color="white" />
        </TouchableOpacity>
      </View>

      {videoUri && !isRecording && (
        <View className="absolute inset-0 bg-black">
          <View className="absolute top-10 left-0 right-0 items-center z-10">
            <View className="bg-black/50 px-4 py-2 rounded-full">
              <Text className="text-white text-lg">
                Recording completed: {formatTime(time)}
              </Text>
            </View>
          </View>
          <View className="absolute bottom-24 left-0 right-0 flex-row justify-center space-x-4">
            <TouchableOpacity
              onPress={resetRecording}
              className="bg-blue-500 px-6 py-3 rounded-full"
            >
              <Text className="text-white font-bold">Record Again</Text>
            </TouchableOpacity>
          </View>
        </View>
      )}

      <View className="absolute bottom-12 w-full items-center">
        <TouchableOpacity
          onPress={isRecording ? stopRecording : startRecording}
          disabled={!isCameraReady}
          className={`rounded-full p-6 ${
            isRecording ? "bg-red-500" : "bg-white"
          } ${!isCameraReady ? "opacity-50" : ""}`}
        >
          <Ionicons
            name={isRecording ? "stop" : "videocam"}
            size={40}
            color={isRecording ? "white" : "black"}
          />
        </TouchableOpacity>
      </View>

      {!isCameraReady && (
        <View className="absolute bottom-24 w-full items-center">
          <Text className="text-white">Initializing camera...</Text>
        </View>
      )}
    </View>
  );
}
