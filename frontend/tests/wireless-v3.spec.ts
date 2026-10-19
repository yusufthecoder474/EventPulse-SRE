import {test,expect} from '@playwright/test';
import path from 'node:path';
const evidence=process.env.V3_SCREENSHOTS||'../wireless-lab/evidence/v3/browser';
async function guest(page:any){await page.goto('/?lab=wireless');await page.getByRole('button',{name:'Continue as Guest'}).click();await expect(page.getByRole('heading',{name:'Wireless overview',exact:true})).toBeVisible();await expect(page.getByText('association success',{exact:true}).first()).toBeVisible();}
test('private PCAPNG import shows Ethernet evidence limits and WPA2 packet references',async({page})=>{
 await guest(page);await page.getByRole('button',{name:'Packet trace explorer',exact:true}).click();await page.getByLabel('Capture file').setInputFiles(path.resolve('../wireless-lab/fixtures/v3/ethernet-eapol.pcapng'));
 await expect(page.getByRole('button',{name:'Analyze authorized capture'})).toBeDisabled();await page.getByRole('checkbox').check();
 const response=page.waitForResponse(r=>r.url().endsWith('/wireless-lab/imports')&&r.request().method()==='POST');await page.getByRole('button',{name:'Analyze authorized capture'}).click();const result=await response;expect(result.status()).toBe(201);const history=await (await page.request.get('/api/wireless-lab/runs')).json();const body=await (await page.request.get('/api/wireless-lab/runs/'+history[0].id)).json();expect(body.extraction.packet_count).toBe(4);
 await expect(page.getByText('802.11 management-layer evidence unavailable in this capture.',{exact:true})).toBeVisible();await page.screenshot({path:`${evidence}/capture-import.png`,fullPage:true});
 await page.getByRole('button',{name:'Failure investigation',exact:true}).click();await expect(page.getByRole('heading',{name:'HANDSHAKE_COMPLETE',exact:true})).toBeVisible();await expect(page.getByText('frame_4',{exact:true})).toBeVisible();
 const report=await page.request.get(`/api/wireless-lab/runs/${body.id}/export`);expect(report.ok()).toBeTruthy();expect(await report.text()).not.toContain('02:00:00:00:10:01');await page.screenshot({path:`${evidence}/handshake.png`,fullPage:true});
 await page.setViewportSize({width:390,height:844});await expect(page.locator('.sidebar')).not.toBeInViewport();expect(await page.evaluate(()=>document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);await page.screenshot({path:`${evidence}/handshake-mobile.png`,fullPage:true});
});
test('registered controller case and full validation plan have separate execution counters',async({page})=>{
 await guest(page);await page.getByRole('button',{name:'Automated test scenarios',exact:true}).click();await page.getByLabel('Test-plan selector').selectOption('C02');
 let response=page.waitForResponse(r=>r.url().endsWith('/wireless-lab/validations')&&r.request().method()==='POST');await page.getByRole('button',{name:'Run selected validation plan'}).click();expect((await (await response).json()).validation.passed_runs).toBe(1);
 await page.getByRole('button',{name:'Failure investigation',exact:true}).click();await expect(page.getByRole('heading',{name:'STALE_OR_INCONSISTENT_CONTROLLER',exact:true})).toBeVisible();await page.screenshot({path:`${evidence}/controller.png`,fullPage:true});
 await page.getByRole('button',{name:'Automated test scenarios',exact:true}).click();await page.getByLabel('Test-plan selector').selectOption('');response=page.waitForResponse(r=>r.url().endsWith('/wireless-lab/validations')&&r.request().method()==='POST');await page.getByRole('button',{name:'Run selected validation plan'}).click();const data=await (await response).json();expect(data.validation).toMatchObject({unique_scenarios:24,executed_runs:24,passed_runs:24,validation_failures:0});
 await expect(page.getByRole('link',{name:'Export test-plan CSV'})).toBeVisible();await expect(page.locator('.wl-v3 tbody tr')).toHaveCount(24);await page.screenshot({path:`${evidence}/test-plan.png`,fullPage:true});
});
