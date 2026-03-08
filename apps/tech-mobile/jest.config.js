module.exports = {
  preset: 'jest-expo',
  moduleNameMapper: {
    '^@office-hero/api-client$': '<rootDir>/../../packages/api-client/src',
    '^@office-hero/types$': '<rootDir>/../../packages/types/src',
  },
};
