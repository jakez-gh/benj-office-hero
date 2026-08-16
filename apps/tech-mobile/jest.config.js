module.exports = {
  preset: 'jest-expo',
  // pnpm uses a flat virtual store under node_modules/.pnpm/pkg@ver/node_modules/pkg
  // so we must exclude '.pnpm' from the "should ignore" check; the real package
  // segment (react-native, @react-native, expo …) appears further down the path
  // and is caught by the second group.
  transformIgnorePatterns: [
    'node_modules/(?!(\\.pnpm|(jest-)?react-native|@react-native(-community)?|expo(-modules-core)?|@expo|@unimodules|@office-hero))',
  ],
};
