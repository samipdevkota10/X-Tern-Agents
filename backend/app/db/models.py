"""
SQLAlchemy ORM models for the disruption response planner.
All models use SQLite-compatible types with JSON stored as TEXT.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Disruption(Base):
    """Represents a warehouse or supply chain disruption."""

    __tablename__ = "disruptions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    type: Mapped[str] = mapped_column(String, nullable=False)  # late_truck, stockout, machine_down
    severity: Mapped[int] = mapped_column(Integer, nullable=False)  # 1-5
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    details_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON as TEXT
    status: Mapped[str] = mapped_column(String, nullable=False, default="open")  # open, resolved

    # Relationships
    scenarios: Mapped[list["Scenario"]] = relationship(
        "Scenario", back_populates="disruption", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (Index("ix_disruptions_type", "type"),)


class Order(Base):
    """Represents a customer order."""

    __tablename__ = "orders"

    order_id: Mapped[str] = mapped_column(String, primary_key=True)
    priority: Mapped[str] = mapped_column(String, nullable=False)  # standard, expedited, vip
    promised_ship_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    cutoff_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    dc: Mapped[str] = mapped_column(String, nullable=False)  # DC1, DC2
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="open"
    )  # open, planned, shipped, delayed
    sequence_priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5
    )  # 1=urgent, 5=normal

    # Relationships
    lines: Mapped[list["OrderLine"]] = relationship(
        "OrderLine", back_populates="order", cascade="all, delete-orphan"
    )
    scenarios: Mapped[list["Scenario"]] = relationship(
        "Scenario", back_populates="order", cascade="all, delete-orphan"
    )


class OrderLine(Base):
    """Represents a line item within an order."""

    __tablename__ = "order_lines"

    line_id: Mapped[str] = mapped_column(String, primary_key=True)
    order_id: Mapped[str] = mapped_column(
        String, ForeignKey("orders.order_id", ondelete="CASCADE"), nullable=False
    )
    sku: Mapped[str] = mapped_column(String, nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="lines")


class Inventory(Base):
    """Represents inventory at a distribution center."""

    __tablename__ = "inventory"

    inv_id: Mapped[str] = mapped_column(String, primary_key=True)
    dc: Mapped[str] = mapped_column(String, nullable=False)
    sku: Mapped[str] = mapped_column(String, nullable=False)
    on_hand: Mapped[int] = mapped_column(Integer, nullable=False)
    reserved: Mapped[int] = mapped_column(Integer, nullable=False)

    # Constraints
    __table_args__ = (UniqueConstraint("dc", "sku", name="uix_inventory_dc_sku"),)


class InboundShipment(Base):
    """Represents an inbound truck shipment."""

    __tablename__ = "inbound_shipments"

    truck_id: Mapped[str] = mapped_column(String, primary_key=True)
    eta: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    dc: Mapped[str] = mapped_column(String, nullable=False)
    sku_list_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON as TEXT


class Capacity(Base):
    """Represents operational capacity at a distribution center."""

    __tablename__ = "capacity"

    cap_id: Mapped[str] = mapped_column(String, primary_key=True)
    dc: Mapped[str] = mapped_column(String, nullable=False)
    process: Mapped[str] = mapped_column(String, nullable=False)  # picking, packing, shipping
    capacity_per_hour: Mapped[int] = mapped_column(Integer, nullable=False)
    downtime_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Substitution(Base):
    """Represents product substitution options."""

    __tablename__ = "substitutions"

    sub_id: Mapped[str] = mapped_column(String, primary_key=True)
    sku: Mapped[str] = mapped_column(String, nullable=False)
    substitute_sku: Mapped[str] = mapped_column(String, nullable=False)
    penalty_cost: Mapped[float] = mapped_column(Float, nullable=False)


class Scenario(Base):
    """Represents a proposed response scenario to a disruption."""

    __tablename__ = "scenarios"

    scenario_id: Mapped[str] = mapped_column(String, primary_key=True)
    disruption_id: Mapped[str] = mapped_column(
        String, ForeignKey("disruptions.id", ondelete="CASCADE"), nullable=False
    )
    order_id: Mapped[str] = mapped_column(
        String, ForeignKey("orders.order_id", ondelete="CASCADE"), nullable=False
    )
    action_type: Mapped[str] = mapped_column(
        String, nullable=False
    )  # delay, reroute, substitute, resequence
    plan_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON as TEXT
    score_json: Mapped[str] = mapped_column(Text, nullable=False)  # JSON as TEXT
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="pending"
    )  # pending, approved, rejected
    used_llm: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )  # True if generated by LLM
    llm_rationale: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # LLM explanation if available
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    disruption: Mapped["Disruption"] = relationship("Disruption", back_populates="scenarios")
    order: Mapped["Order"] = relationship("Order", back_populates="scenarios")

    # Indexes
    __table_args__ = (Index("ix_scenarios_status", "status"),)


class DecisionLog(Base):
    """
    Logs decisions made by agents or humans in the response pipeline.
    This table exactly matches the required schema for tracking approvals,
    rejections, and other decision points.
    """

    __tablename__ = "decision_logs"

    log_id: Mapped[str] = mapped_column(String, primary_key=True)
    timestamp: Mapped[str] = mapped_column(String, nullable=False)  # ISO8601 as TEXT
    pipeline_run_id: Mapped[str] = mapped_column(String, nullable=False)
    agent_name: Mapped[str] = mapped_column(String, nullable=False)
    input_summary: Mapped[str] = mapped_column(String, nullable=False)
    output_summary: Mapped[str] = mapped_column(String, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    rationale: Mapped[str] = mapped_column(String, nullable=False)
    human_decision: Mapped[str] = mapped_column(
        String, nullable=False
    )  # approved, rejected, edited, pending
    approver_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    approver_note: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    override_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON as TEXT

    # Indexes
    __table_args__ = (Index("ix_decision_logs_pipeline_run_id", "pipeline_run_id"),)


class PipelineRun(Base):
    """
    Tracks execution of multi-agent pipeline runs.
    Stores final unified recommendations and metadata.
    """

    __tablename__ = "pipeline_runs"

    pipeline_run_id: Mapped[str] = mapped_column(String, primary_key=True)
    disruption_id: Mapped[str] = mapped_column(
        String, ForeignKey("disruptions.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="queued"
    )  # queued, running, done, failed
    current_step: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)  # 0.0 to 1.0
    started_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    final_summary_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON as TEXT
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Indexes
    __table_args__ = (Index("ix_pipeline_runs_disruption_id", "disruption_id"),)


class User(Base):
    """Represents a user with authentication credentials."""

    __tablename__ = "users"

    user_id: Mapped[str] = mapped_column(String, primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)  # warehouse_manager, analyst
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )
