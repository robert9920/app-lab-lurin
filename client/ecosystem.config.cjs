module.exports = {
  apps: [
    {
      name: "lab-portal",
      script: "./server.mjs",
      instances: 1,
      exec_mode: "fork",
      autorestart: true,
      env: { NODE_ENV: "production" },
    },
  ],
};
