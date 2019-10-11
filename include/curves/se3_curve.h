#ifndef _STRUCT_SE3_CURVE_H
#define _STRUCT_SE3_CURVE_H


#include "MathDefs.h"
#include "curve_abc.h"
#include "so3_linear.h"
#include "polynomial.h"
#include <boost/math/constants/constants.hpp>
#include <Eigen/Dense>

namespace curves
{

  /// \class SE3Curve.
  /// \brief Composition of a curve of any type of dimension 3 and a curve representing an rotation
  /// (in current implementation, only SO3Linear can be used for the rotation part)
  /// The output is a vector of size 7 (pos_x,pos_y,pos_z,quat_x,quat_y,quat_z,quat_w)
  /// The output of the derivative of any order is a vector of size 6 (linear_x,linear_y,linear_z,angular_x,angular_y,angular_z)
  ///
  ///
  template<typename Time= double, typename Numeric=Time, bool Safe=false>
  struct SE3Curve : public curve_abc<Time, Numeric, Safe, Eigen::Transform<Numeric,3,Eigen::Affine>,Eigen::Matrix<Numeric,6, 1> >
  {
    typedef Numeric Scalar;
    typedef Eigen::Transform<Numeric,3,Eigen::Affine> transform_t;
    typedef transform_t point_t;
    typedef Eigen::Matrix<Scalar,6, 1> point_derivate_t;
    typedef Eigen::Matrix<Scalar,3, 1> point3_t;
    typedef Eigen::Matrix<Scalar, -1, 1> pointX_t;
    typedef Eigen::Matrix<Scalar,3, 3> matrix3_t;
    typedef Eigen::Quaternion<Scalar> Quaternion;
    typedef Time  time_t;
    typedef curve_abc<Time, Numeric, Safe, point_t,point_derivate_t> curve_abc_t; // parent class
    typedef curve_abc<Time, Numeric, Safe, pointX_t> curve_X_t; // generic class of curve
    typedef curve_abc<Time, Numeric, Safe, matrix3_t,point3_t> curve_rotation_t; // templated class used for the rotation (return dimension are fixed)
    typedef SO3Linear<Time, Numeric, Safe> SO3Linear_t;
    typedef polynomial  <Time, Numeric, Safe, pointX_t> polynomial_t;
    typedef SE3Curve<Time, Numeric, Safe> SE3Curve_t;


  public:
    /* Constructors - destructors */
    /// \brief Empty constructor. Curve obtained this way can not perform other class functions.
    ///
    SE3Curve()
      : curve_abc_t(), dim_(3),translation_curve_(NULL),rotation_curve_ (NULL), T_min_(0), T_max_(0)
    { }

    /// \brief Destructor
    ~SE3Curve()
    {
      // should we delete translation_curve and rotation_curve here ?
      // better switch to shared ptr
    }


    /* Constructor without curve object for the translation : */
    /// \brief Constructor from init/end transform use polynomial of degree 1 for position and SO3Linear for rotation
    SE3Curve(const transform_t& init_transform, const transform_t& end_transform,const time_t& t_min, const time_t& t_max)
      : curve_abc_t(),
        dim_(6),
        translation_curve_(new polynomial_t(pointX_t(init_transform.translation()),pointX_t(end_transform.translation()),t_min,t_max)),
        rotation_curve_(new SO3Linear_t(init_transform.rotation(),end_transform.rotation(),t_min,t_max)),
        T_min_(t_min), T_max_(t_max)
    {
      safe_check();
    }

    /// \brief Constructor from init/end pose, with quaternion. use polynomial of degree 1 for position and SO3Linear for rotation
    SE3Curve(const pointX_t& init_pos, const pointX_t& end_pos, const Quaternion& init_rot, const Quaternion& end_rot,const time_t& t_min, const time_t& t_max)
      : curve_abc_t(),
        dim_(6),translation_curve_(new polynomial_t(init_pos,end_pos,t_min,t_max)),
        rotation_curve_(new SO3Linear_t(init_rot,end_rot,t_min,t_max)),
        T_min_(t_min), T_max_(t_max)
    {
      safe_check();
    }

    /// \brief Constructor from init/end pose, with rotation matrix. use polynomial of degree 1 for position and SO3Linear for rotation
    SE3Curve(const pointX_t& init_pos, const pointX_t& end_pos, const matrix3_t& init_rot, const matrix3_t& end_rot,const time_t& t_min, const time_t& t_max)
      : curve_abc_t(),
        dim_(6),translation_curve_(new polynomial_t(init_pos,end_pos,t_min,t_max)),
        rotation_curve_(new SO3Linear_t(init_rot,end_rot,t_min,t_max)),
        T_min_(t_min), T_max_(t_max)
    {
      safe_check();
    }

    /* Constructor with curve object for the translation : */
    /// \brief Constructor from curve for the translation and init/end rotation, with quaternion.
    /// Use SO3Linear for rotation with the same time bounds as the
    SE3Curve(curve_X_t* translation_curve,const Quaternion& init_rot, const Quaternion& end_rot)
      : curve_abc_t(),
        dim_(6),translation_curve_(translation_curve),
        rotation_curve_(new SO3Linear_t(init_rot,end_rot,translation_curve->min(),translation_curve->max())),
        T_min_(translation_curve->min()), T_max_(translation_curve->max())
    {
      safe_check();
    }
    /// \brief Constructor from curve for the translation and init/end rotation, with rotation matrix.
    /// Use SO3Linear for rotation with the same time bounds as the
    SE3Curve(curve_X_t* translation_curve,const matrix3_t& init_rot, const matrix3_t& end_rot)
      : curve_abc_t(),
        dim_(6),translation_curve_(translation_curve),
        rotation_curve_(new SO3Linear_t(init_rot,end_rot,translation_curve->min(),translation_curve->max())),
        T_min_(translation_curve->min()), T_max_(translation_curve->max())
    {
      safe_check();
    }

    /* Constructor from translation and rotation curves object : */
    /// \brief Constructor from from translation and rotation curves object
    SE3Curve(curve_X_t* translation_curve,curve_rotation_t* rotation_curve)
      : curve_abc_t(),
        dim_(6),translation_curve_(translation_curve),
        rotation_curve_(rotation_curve),
        T_min_(translation_curve->min()), T_max_(translation_curve->max())
    {
      if(translation_curve->dim() != 3 ){
        throw std::invalid_argument("The translation curve should be of dimension 3.");
      }
      if(rotation_curve->min() != T_min_){
        throw std::invalid_argument("Min bounds of translation and rotation curve are not the same.");
      }
      if(rotation_curve->max() != T_max_){
        throw std::invalid_argument("Max bounds of translation and rotation curve are not the same.");
      }
      safe_check();
    }



    ///  \brief Evaluation of the SE3Curve at time t
    ///  \param t : time when to evaluate the spline.
    ///  \return \f$x(t)\f$ point corresponding on spline at time t. (pos_x,pos_y,pos_z,quat_x,quat_y,quat_z,quat_w)
    virtual point_t operator()(const time_t t) const
    {
      if(translation_curve_->dim() != 3){
        throw std::invalid_argument("Translation curve should always be of dimension 3");
      }
      point_t res = point_t::Identity();
      res.translate(point3_t((*translation_curve_)(t)));
      res.rotate((*rotation_curve_)(t));
      return res;
    }

    ///  \brief Evaluation of the derivative of order N of spline at time t.
    ///  \param t : the time when to evaluate the spline.
    ///  \param order : order of derivative.
    ///  \return \f$\frac{d^Nx(t)}{dt^N}\f$ point corresponding on derivative spline at time t.
    virtual point_derivate_t derivate(const time_t t, const std::size_t order) const
    {
      if(translation_curve_->dim() != 3){
        throw std::invalid_argument("Translation curve should always be of dimension 3");
      }
      point_derivate_t res = point_derivate_t::Zero();
      res.segment(0,3) = point3_t(translation_curve_->derivate(t,order));
      res.segment(3,3) = rotation_curve_->derivate(t,order);
      return res;
    }



    /*Helpers*/
    /// \brief Get dimension of curve.
    /// \return dimension of curve.
    std::size_t virtual dim() const{return dim_;};
    /// \brief Get the minimum time for which the curve is defined
    /// \return \f$t_{min}\f$ lower bound of time range.
    time_t min() const {return T_min_;}
    /// \brief Get the maximum time for which the curve is defined.
    /// \return \f$t_{max}\f$ upper bound of time range.
    time_t max() const {return T_max_;}
    /*Helpers*/

    /*Attributes*/
    std::size_t dim_; //dim doesn't mean anything in this class ...
    curve_X_t* translation_curve_ = NULL;
    curve_rotation_t* rotation_curve_= NULL;
    time_t T_min_, T_max_;
    /*Attributes*/


    // Serialization of the class
    friend class boost::serialization::access;

    template<class Archive>
    void serialize(Archive& ar, const unsigned int version){
      if (version) {
        // Do something depending on version ?
      }
      ar & boost::serialization::make_nvp("dim", dim_);
      ar & boost::serialization::make_nvp("translation_curve", translation_curve_);
      ar & boost::serialization::make_nvp("rotation_curve", rotation_curve_);
      ar & boost::serialization::make_nvp("T_min", T_min_);
      ar & boost::serialization::make_nvp("T_max", T_max_);
    }

  private:
    void safe_check()
    {
      if(Safe)
      {
        if(T_min_ > T_max_)
        {
          throw std::invalid_argument("Tmin should be inferior to Tmax");
        }
        if(translation_curve_->dim() != 3){
          throw std::invalid_argument("Translation curve should always be of dimension 3");
        }
      }
    }



  };//SE3Curve

} // namespace curve



#endif // SE3_CURVE_H
