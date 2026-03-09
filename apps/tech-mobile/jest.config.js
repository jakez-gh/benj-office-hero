module.exports = {
  preset: 'jest-expo',
  transformIgnorePatterns: [
    'node_modules/(?!(react-native|@react-native|expo|@expo|expo-modules|@unimodules)/)'
  ],
  setupFilesAfterEnv: ['@testing-library/jest-native/extend-expect'],
};
