standardConfig static_configs[] = {
    createBoolConfig("daemonize", NULL, IMMUTABLE_CONFIG, server.daemonize, 0, NULL, NULL),
    createIntConfig("databases", NULL, IMMUTABLE_CONFIG, 1, INT_MAX, server.dbnum, 16, INTEGER_CONFIG, NULL, NULL),
    createStringConfig("tls-auth-clients-user", NULL, MODIFIABLE_CONFIG, ALLOW_EMPTY_STRING, server.x, NULL, NULL, NULL),
    createBoolConfig("secret-knob", NULL, MODIFIABLE_CONFIG | HIDDEN_CONFIG, server.y, 0, NULL, NULL),
    createIntConfig("undocumented-knob", "old-knob", MODIFIABLE_CONFIG, 0, 10, server.z, 1, INTEGER_CONFIG, NULL, NULL),
};
