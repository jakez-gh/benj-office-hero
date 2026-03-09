import React, { useState } from 'react';
import { View, Text, TextInput, Button, StyleSheet, Alert } from 'react-native';
import { createJob } from '@office-hero/api-client';

export type JobEntryScreenProps = {
  token: string;
  onCreated?: (jobId: string) => void;
};

export default function JobEntryScreen({ token, onCreated }: JobEntryScreenProps) {
  const [customerName, setCustomerName] = useState('');
  const [address, setAddress] = useState('');
  const [description, setDescription] = useState('');
  const [busy, setBusy] = useState(false);

  const handleSubmit = async () => {
    if (!customerName || !address) {
      Alert.alert('Required', 'Customer name and address are required');
      return;
    }
    setBusy(true);
    try {
      const res = await createJob(token, { customerName, address, description });
      Alert.alert('Job Created', `Job ID: ${res.jobId}`);
      onCreated?.(res.jobId);
    } catch (err: any) {
      Alert.alert('Error', err.message || String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>New Job</Text>
      <TextInput
        placeholder="Customer Name"
        value={customerName}
        onChangeText={setCustomerName}
        style={styles.input}
      />
      <TextInput
        placeholder="Address"
        value={address}
        onChangeText={setAddress}
        style={styles.input}
      />
      <TextInput
        placeholder="Description (optional)"
        value={description}
        onChangeText={setDescription}
        style={styles.input}
      />
      <Button title={busy ? 'Creating...' : 'Create Job'} onPress={handleSubmit} disabled={busy} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 16 },
  title: { fontSize: 24, marginBottom: 16, textAlign: 'center' },
  input: { borderWidth: 1, borderColor: '#ccc', padding: 8, marginBottom: 12, borderRadius: 4 },
});
