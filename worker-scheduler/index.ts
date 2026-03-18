export default {
  async scheduled(event: any, env: any, ctx: any) {
    const pagesUrl = "https://stock-trading-top-10.pages.dev/api/report";
    
    // Trigger US Market report
    console.log("Triggering US market report...");
    await fetch(`${pagesUrl}?market=US`, {
      headers: { "Authorization": `Bearer ${env.CRON_SECRET}` }
    });

    // Trigger KR Market report
    console.log("Triggering KR market report...");
    await fetch(`${pagesUrl}?market=KR`, {
      headers: { "Authorization": `Bearer ${env.CRON_SECRET}` }
    });

    console.log("Reports triggered successfully.");
  },
};
