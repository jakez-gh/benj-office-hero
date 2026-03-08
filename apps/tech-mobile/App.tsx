import React, { useState } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import LoginScreen from './LoginScreen';
import RouteScreen from './RouteScreen';
import JobEntryScreen from './JobEntryScreen';

export type RootStackParamList = {
  Login: undefined;
  Route: undefined;
  JobEntry: undefined;
};

const Stack = createNativeStackNavigator();

export default function App() {
  const [token, setToken] = useState<string | null>(null);

  return (
    <NavigationContainer>
      <Stack.Navigator>
        {token == null ? (
          <Stack.Screen name="Login">
            {() => <LoginScreen onLogin={setToken} />}
          </Stack.Screen>
        ) : (
          <>
            <Stack.Screen name="Route">
              {({ navigation }: { navigation: any }) => <RouteScreen token={token} navigation={navigation} />}
            </Stack.Screen>
            <Stack.Screen name="JobEntry">
              {() => <JobEntryScreen token={token} />}
            </Stack.Screen>
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}
