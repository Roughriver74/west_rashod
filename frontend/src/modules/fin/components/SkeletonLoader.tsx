import { motion } from 'framer-motion';
import { Skeleton, Card, Row, Col } from 'antd';

export const SkeletonCard = () => (
  <motion.div
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
  >
    <Card bodyStyle={{ padding: 20 }}>
      <Skeleton active paragraph={{ rows: 2 }} />
    </Card>
  </motion.div>
);

export const SkeletonChart = () => (
  <motion.div
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
  >
    <Card bodyStyle={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <Skeleton.Node active style={{ width: '100%', height: 350 }}>
        <div style={{ width: '100%', height: 350 }} />
      </Skeleton.Node>
    </Card>
  </motion.div>
);

interface SkeletonTextProps {
  lines?: number;
}

export const SkeletonText = ({ lines = 3 }: SkeletonTextProps) => (
  <div style={{ padding: 20 }}>
    {Array.from({ length: lines }).map((_, i) => (
      <motion.div
        key={i}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: i * 0.1 }}
        style={{ marginBottom: 12 }}
      >
        <Skeleton.Input
          active
          size="small"
          style={{ width: `${100 - i * 10}%` }}
        />
      </motion.div>
    ))}
  </div>
);

export const DashboardSkeleton = () => (
  <div style={{ padding: 20 }}>
    {/* Header */}
    <div style={{ marginBottom: 24 }}>
      <Skeleton.Input active size="large" style={{ width: 300, marginBottom: 8 }} />
      <Skeleton.Input active size="small" style={{ width: 200 }} />
    </div>

    {/* KPI Cards */}
    <Row gutter={[16, 16]} style={{ marginBottom: 32 }}>
      {Array.from({ length: 5 }).map((_, i) => (
        <Col xs={24} sm={12} lg={4} key={i}>
          <SkeletonCard />
        </Col>
      ))}
    </Row>

    {/* Active Credits Section */}
    <Card style={{ marginBottom: 32 }}>
      <Skeleton.Input active size="default" style={{ width: 200, marginBottom: 16 }} />
      <Skeleton active paragraph={{ rows: 6 }} />
    </Card>

    {/* Charts */}
    <Row gutter={[16, 16]}>
      <Col span={24}>
        <SkeletonChart />
      </Col>
      <Col span={12}>
        <SkeletonChart />
      </Col>
      <Col span={12}>
        <SkeletonChart />
      </Col>
    </Row>
  </div>
);

export default {
  Card: SkeletonCard,
  Chart: SkeletonChart,
  Text: SkeletonText,
  Dashboard: DashboardSkeleton,
};
