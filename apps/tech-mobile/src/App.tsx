import React, { useState, useContext } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, SafeAreaView } from 'react-native';
import { StatusBar } from 'expo-status-bar';

/**
 * Placeholder Tech Mobile App
 * Future implementation: React Native Expo auth flow, route viewing, location tracking
 */
export default function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  return (
    <SafeAreaView style={styles.container}>
      <StatusBar barStyle="dark-content" />
      <View style={styles.content}>
        <Text style={styles.title}>Office Hero</Text>
        <Text style={styles.subtitle}>Technician Mobile App</Text>

        {!isLoggedIn ? (
          <>
            <Text style={styles.placeholder}>Login Implementation Coming Soon</Text>
            <TouchableOpacity
              style={styles.button}
              onPress={() => setIsLoggedIn(true)}
            >
              <Text style={styles.buttonText}>Demo Login</Text>
            </TouchableOpacity>
          </>
        ) : (
          <>
            <Text style={styles.placeholder}>Route and Location Tracking Coming Soon</Text>
            <TouchableOpacity
              style={styles.button}
              onPress={() => setIsLoggedIn(false)}
            >
              <Text style={styles.buttonText}>Logout</Text>
            </TouchableOpacity>
          </>
        )}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5'
  },
  content: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    marginBottom: 8,
    color: '#333'
  },
  subtitle: {
    fontSize: 16,
    color: '#666',
    marginBottom: 40
  },
  placeholder: {
    fontSize: 14,
    color: '#999',
    marginBottom: 20,
    textAlign: 'center'
  },
  button: {
    backgroundColor: '#007AFF',
    paddingVertical: 12,
    paddingHorizontal: 40,
    borderRadius: 8,
    marginTop: 20
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600'
  }
});
