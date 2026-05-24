module.exports = {
  preset: 'jest-expo',
  transformIgnorePatterns: [
    'node_modules/(?!(react-native|@react-native|expo|@expo|expo-modules|@unimodules|@react-native/js-polyfills)/)'
  ],
  setupFilesAfterEnv: ['@testing-library/jest-native/extend-expect'],
};
