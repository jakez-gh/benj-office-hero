import React, { useEffect, useState } from 'react';
import { View, Text, Button, FlatList, StyleSheet, ActivityIndicator } from 'react-native';
import { getDailyRoute, acknowledgeStop } from '@office-hero/api-client';
import type { Route, Stop } from '@office-hero/types';

export type RouteScreenProps = {
  token: string;
  navigation: any;
};

export default function RouteScreen({ token, navigation }: RouteScreenProps) {
  const [route, setRoute] = useState<Route | null>(null);
  const [loading, setLoading] = useState(true);
  const [ackInProgress, setAckInProgress] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const r = await getDailyRoute(token);
        setRoute(r);
      // start background tracking if we have a vehicleId
      if (r.vehicleId) {
        import('./LocationService').then(({ startLocationTracking }) =>
          startLocationTracking(token, r.vehicleId!)
        );
      }
      } catch (err) {
        console.error('failed to load route', err);
      } finally {
        setLoading(false);
      }
    })();
  }, [token]);

  const handleAcknowledge = async (stop: Stop) => {
    setAckInProgress(stop.id);
    try {
      await acknowledgeStop(token, stop.id);
      setRoute((r) =>
        r
          ? {
              ...r,
              stops: r.stops.map((s) =>
                s.id === stop.id ? { ...s, acknowledged: true } : s
              ),
            }
          : r
      );
    } catch (err) {
      console.error('ack failed', err);
    } finally {
      setAckInProgress(null);
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" />
        <Text>Loading route...</Text>
      </View>
    );
  }

  if (!route) {
    return (
      <View style={styles.center}>
        <Text>No route available</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Today's Stops</Text>
      <Button title="New Job" onPress={() => navigation.navigate('JobEntry')} />
      <FlatList
        data={route.stops}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <View style={styles.stopRow}>
            <Text style={styles.address}>{item.address}</Text>
            {!item.acknowledged && (
              <Button
                title={ackInProgress === item.id ? '...' : 'Acknowledge'}
                onPress={() => handleAcknowledge(item)}
                disabled={ackInProgress !== null}
              />
            )}
            {item.acknowledged && <Text style={styles.done}>✔️</Text>}
          </View>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: { fontSize: 24, marginBottom: 16, textAlign: 'center' },
  stopRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 12 },
  address: { flex: 1 },
  done: { marginLeft: 8, color: 'green' },
});
