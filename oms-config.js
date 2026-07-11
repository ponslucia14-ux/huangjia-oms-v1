(() => {
  const hostname = String(window.location.hostname || "").toLowerCase();
  const localHostnames = new Set(["localhost", "127.0.0.1", "::1", ""]);
  const requestedEnvironment = String(window.OMS_ENV || "").toLowerCase();
  const environment = requestedEnvironment || (localHostnames.has(hostname) ? "development" : "production");
  const configs = window.OMS_ENV_CONFIGS || {};
  const config = configs[environment];

  if (!config) {
    throw new Error(`oms_environment_config_missing:${environment}`);
  }
  if (environment === "production" && !String(config.apiBaseUrl || "").startsWith("https://")) {
    throw new Error("oms_production_api_must_use_https");
  }

  const apiBaseUrl = String(config.apiBaseUrl || "").replace(/\/$/, "");
  window.OMS_ENV = environment;
  window.OMS_CONFIG_VERSION = config.configVersion;
  window.OMS_FEISHU_APP_ID = config.feishuAppId;
  window.OMS_FEISHU_REDIRECT_URI = config.feishuRedirectUri;
  window.OMS_FEISHU_SCOPE_LIST = [];
  window.OMS_AUTH_ENDPOINT = `${apiBaseUrl}/api/feishu/identity`;
  window.OMS_HOME_ENDPOINT = `${apiBaseUrl}/api/oms/home`;
  window.OMS_EXECUTE_ENDPOINT = `${apiBaseUrl}/api/oms/execute`;
  window.OMS_LOCAL_OWNER_ACCESS_ENDPOINT = `${apiBaseUrl}/api/oms/local-owner-access`;
  window.OMS_LOCAL_OWNER_ACCESS_ENABLED = Boolean(config.localOwnerAccessEnabled);
  window.OMS_CONTRACT_VERSION = "oms.contract.v1.0";
  window.OMS_CONTRACT_URL = `./contract.json?v=${encodeURIComponent(config.assetVersion)}`;
  window.OMS_RUNTIME_SOURCE = "OMS_TRUTH_SOURCE";
  window.OMS_CLOUD_ROLE = "request_forwarding_only";
  window.OMS_REMOTE_DATA_GENERATION_ALLOWED = false;
  window.OMS_FEISHU_USER_WORKSPACE_MAP = window.OMS_FEISHU_USER_WORKSPACE_MAP || {};
})();
