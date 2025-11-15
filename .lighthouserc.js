module.exports = {
  ci: {
    collect: {
      // Use the already running server instead of starting a new one
      startServerCommand: null,
      // URL to test (server should already be running)
      url: ['http://localhost:3000'],
      // Number of runs per URL
      numberOfRuns: 1,
      settings: {
        // Chrome flags for CI environment
        chromeFlags: '--no-sandbox --disable-dev-shm-usage --headless',
      },
    },
    upload: {
      // Store results in local directory
      target: 'filesystem',
      outputDir: '.lighthouseci',
    },
  },
};
