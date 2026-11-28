'use client';

import Link from 'next/link';
import { AccountSetup } from './AccountSetup';
import { useEffect, useState } from 'react';

const instructions = [
  { title: 'Place the band above the wrist bone', detail: 'Keep the screen facing up and leave a little room to move your wrist.' },
  { title: 'Adjust the strap so it sits comfortably', detail: 'Fasten it until it stays in place when you gently move your wrist.' },
  { title: 'Keep the sensor against the skin', detail: 'Check that the back of the band sits flat against your wrist.' },
];

export default function SetupPage() {
  const [stage, setStage] = useState<'account' | 'guide' | 'complete'>('account');
  const [instruction, setInstruction] = useState(0);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('step') === 'guide' && sessionStorage.getItem('jagsi-preview-intake') === 'done') {
      setStage('guide');
    }
  }, []);

  useEffect(() => {
    if (stage !== 'guide') return;
    const timer = window.setTimeout(() => setReady(true), 3000);
    return () => window.clearTimeout(timer);
  }, [stage]);

  if (stage === 'account') return <AccountSetup />;

  return (
    <div className="onboarding-shell">
      <Link className="ungu-brand" href="/"><img src="/ungu/brand.svg" alt="" />JagSi</Link>
      {stage === 'guide' && <>
        <h1>Wear your JagSi Smartband</h1>
        <p>Place the band on the left wrist.</p>
        <section className="ungu-panel wrist-guide">
          <div className="wrist-guide-counter">Left wrist / {String(instruction + 1).padStart(2, '0')} of 03</div>
          <img src="/ungu/left-wrist.svg" width={302} height={194} alt="JagSi band positioned above the left wrist bone" />
          <div aria-live="polite" className="grid gap-4">
            <h2>{instructions[instruction].title}</h2>
            <p>{instructions[instruction].detail}</p>
          </div>
          <button className="ungu-action bg-white text-on-surface" type="button"
            onClick={() => setInstruction((instruction + 1) % instructions.length)}>
            {instruction === instructions.length - 1 ? 'Review from step 1' : 'Next step'}
          </button>
          <span role="status" className="sr-only">{ready ? 'Confirm fit is available.' : ''}</span>
          {ready && <button className="landing-cta justify-self-start" type="button"
            onClick={() => { sessionStorage.removeItem('jagsi-preview-intake'); setStage('complete'); }}>Confirm fit</button>}
        </section>
      </>}
      {stage === 'complete' && <>
        <h1>Setup complete</h1>
        <p>Your Smartband guide is ready whenever you need it.</p>
        <section className="ungu-panel wrist-guide">
          <div className="wrist-guide-counter">04 / Setup complete</div>
          <img src="/ungu/setup-complete.svg" width={302} height={160} alt="" />
          <h2>Your guide is complete</h2>
          <p>Open the live dashboard to check your Smartband connection.</p>
          <Link className="landing-cta justify-self-start" href="/beranda">See live</Link>
        </section>
      </>}
    </div>
  );
}
