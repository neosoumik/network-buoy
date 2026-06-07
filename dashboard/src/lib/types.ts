export type BuoyEvent = {
  timestamp: string;
  event: "connection" | "credential";
  protocol: string;
  ip: string;
  // connection events
  data?: string;
  // credential events
  username?: string;
  password?: string;
  token?: string;
  // ssh extras
  method?: string;
};
