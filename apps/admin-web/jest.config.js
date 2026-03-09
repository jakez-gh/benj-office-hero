module.exports = {
  roots: ['<rootDir>/src'],
  testPathIgnorePatterns: ['/node_modules/', '<rootDir>/src/e2e/'],
  transform: {
    '^.+\\.tsx?$': 'ts-jest'
  },
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/src/setupTests.ts'],
  moduleNameMapper: {
    '^@office-hero/(.*)$': '<rootDir>/../../packages/$1/src'
  }
};
