// shim declarations so TypeScript can find navigation packages when they are hoisted

declare module '@react-navigation/native' {
  import { ComponentType, PropsWithChildren } from 'react';
  export const NavigationContainer: ComponentType<PropsWithChildren<any>>;
}

declare module '@react-navigation/native-stack' {
  export function createNativeStackNavigator(): any;
}
