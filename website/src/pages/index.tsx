import type {ReactNode} from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';

import styles from './index.module.css';

type Feature = {
  title: string;
  description: string;
};

const FEATURES: Feature[] = [
  {
    title: 'Distance or time',
    description:
      'A maintenance job has a distance interval, a time interval or both. It comes due at the first limit.',
  },
  {
    title: 'Odometer with or without a sensor',
    description:
      'Type the odometer reading, or bind it to the odometer sensor of a car integration.',
  },
  {
    title: 'Home Keeper tasks',
    description:
      'Each job is a Home Keeper task, so the to-do list, the calendar and the notifications of Home Keeper work for cars.',
  },
  {
    title: 'Cards, entities and services',
    description:
      'Every user gets dashboard cards and the sensors of each car. Each data action is a service, and each change fires an event.',
  },
];

function HomepageHeader() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <header className={clsx('hero', styles.heroBanner)}>
      <div className="container">
        <Heading as="h1" className={styles.heroTitle}>
          {siteConfig.title}
        </Heading>
        <p className={styles.heroTagline}>{siteConfig.tagline}</p>
        <div className={styles.buttons}>
          <Link className="button button--secondary button--lg" to="/docs/intro">
            User Guide
          </Link>
          <Link
            className="button button--outline button--secondary button--lg"
            to="/developer/integrating">
            Developer Guide
          </Link>
        </div>
      </div>
    </header>
  );
}

function HomepageFeatures() {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FEATURES.map((feature) => (
            <div key={feature.title} className={clsx('col col--6', styles.feature)}>
              <Heading as="h3">{feature.title}</Heading>
              <p>{feature.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export default function Home(): ReactNode {
  const {siteConfig} = useDocusaurusContext();
  return (
    <Layout title={siteConfig.title} description={siteConfig.tagline}>
      <HomepageHeader />
      <main>
        <HomepageFeatures />
      </main>
    </Layout>
  );
}
