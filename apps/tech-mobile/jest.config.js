// Packages that ship untranspiled ESM/Flow and must be run through Babel.
// With pnpm, dependencies live under node_modules/.pnpm/<pkg>@<version>/...,
// so the pattern must allow both the classic and the .pnpm path layouts.
const transpilePackages = [
  'react-native',
  '@react-native',
  'expo',
  'expo-.*',
  '@expo',
  '@expo-google-fonts',
  '@unimodules',
  'unimodules-.*',
  '@react-navigation',
  'react-navigation',
  'react-native-.*',
].join('|');

module.exports = {
  preset: 'jest-expo',
  // jest-expo suites are slow to boot (React Native transform); the default
  // 5s per-test timeout flakes under parallel suite load.
  testTimeout: 30000,
  transformIgnorePatterns: [
    `node_modules/(?!(\\.pnpm/)?(${transpilePackages}))`,
  ],
  setupFilesAfterEnv: ['@testing-library/jest-native/extend-expect'],
};
