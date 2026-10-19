import { fireEvent, render, screen, waitFor, cleanup } from '@testing-library/react';
import { afterEach, expect, test, vi } from 'vitest';
import WirelessV3 from './WirelessV3';
afterEach(()=>{cleanup();vi.unstubAllGlobals();});
test('capture requires explicit consent and submits bytes with a bounded file label',async()=>{
 const response=vi.fn().mockResolvedValue({ok:true,json:async()=>({id:'private-run'})});vi.stubGlobal('fetch',response);const onResult=vi.fn();
 render(<WirelessV3 view={3} selected={null} onResult={onResult}/>);
 const button=screen.getByRole('button',{name:'Analyze authorized capture'});expect(button).toBeDisabled();
 fireEvent.change(screen.getByLabelText('Capture file'),{target:{files:[new File(['pcap'],'lab.pcap')]}});
 expect(button).toBeDisabled();fireEvent.click(screen.getByRole('checkbox'));fireEvent.click(button);
 await waitFor(()=>expect(onResult).toHaveBeenCalledWith({id:'private-run'}));
 const [url,options]=response.mock.calls[0];expect(url).toBe('/api/wireless-lab/imports');expect(options.headers['X-Lab-Authorized']).toBe('true');expect(options.body).toBeInstanceOf(File);
});
test('handshake investigation exposes missing evidence and avoids crypto success claims',()=>{
 render(<WirelessV3 view={5} selected={{id:'run',handshakes:{sessions:[{session_id:'one',classification:'HANDSHAKE_INCOMPLETE',explanation:'Missing captured stage',client:'client_mask',authenticator:'ap_mask',possible_retransmissions:1,missing_messages:[3],packet_references:[{event_id:'frame_4',message:4,timestamp_us:1234,replay_counter:'2',direction:'client_to_ap'}]}]}}} onResult={()=>{}}/>);
 expect(screen.getByRole('heading',{name:'HANDSHAKE_INCOMPLETE'})).toBeVisible();expect(screen.getByText(/missing: 3/)).toBeVisible();expect(screen.getByText('frame_4')).toBeVisible();expect(screen.getByText(/No passwords, MIC verification/)).toBeVisible();
});
test('test-plan selector posts the registered ID and renders an expected negative outcome',async()=>{
 const report={id:'owned',validation:{unique_scenarios:1,executed_runs:1,passed_runs:1,validation_failures:0,results:[]}};
 const fetch=vi.fn().mockResolvedValueOnce({ok:true,json:async()=>({cases:[{id:'B',feature:'Expected AP rejection',kind:'legacy',expected:['association_rejected']}]})}).mockResolvedValueOnce({ok:true,json:async()=>report});vi.stubGlobal('fetch',fetch);const onResult=vi.fn();
 render(<WirelessV3 view={4} selected={report} onResult={onResult}/>);
 await screen.findByRole('option',{name:'B · Expected AP rejection'});fireEvent.change(screen.getByLabelText('Test-plan selector'),{target:{value:'B'}});fireEvent.click(screen.getByRole('button',{name:'Run selected validation plan'}));await waitFor(()=>expect(onResult).toHaveBeenCalledWith(report));expect(JSON.parse(fetch.mock.calls[1][1].body)).toEqual({test_id:'B'});expect(screen.getByRole('link',{name:'Export test-plan CSV'})).toHaveAttribute('href','/api/wireless-lab/runs/owned/validation-export?format=csv');
});
