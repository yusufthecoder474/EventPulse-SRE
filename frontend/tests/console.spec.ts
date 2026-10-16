import { test, expect } from '@playwright/test';
test('real API dashboard, probes, navigation and screenshot', async({page})=>{
 await page.goto('/');
 await expect(page.getByRole('heading',{name:'Operations overview',exact:true})).toBeVisible();
 await expect(page.getByText('Telemetry connected')).toBeVisible();
 await page.getByRole('button',{name:'Send 10 probes'}).click();
 await expect(page.getByText('10 real GET /events probes completed.')).toBeVisible();
 await page.evaluate(()=>window.scrollTo(0,0));
 await page.screenshot({path:'../docs/screenshots/overview.png',fullPage:true});
 for(const name of ['Service monitoring','Incident center','SLO dashboard','Fault injection lab','Experiment results']){
  await page.getByRole('button',{name,exact:true}).click();
  await expect(page.getByRole('heading',{name,exact:true})).toBeVisible();
 }
 await page.screenshot({path:'../docs/screenshots/experiments.png',fullPage:true});
});
test('mobile navigation remains usable',async({page})=>{
 await page.setViewportSize({width:390,height:844});await page.goto('/');
 await page.getByRole('button',{name:'Toggle navigation'}).click();
 await page.getByRole('button',{name:'Service monitoring',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Service monitoring',exact:true})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
 await page.screenshot({path:'../docs/screenshots/mobile.png',fullPage:true});
});
